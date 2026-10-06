"""The three pieces that were silently rotting: mill-rate math, the audit's
local eyes, and the inventory artifact — plus the fixture-migration pass."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ctsignal import audit, config, inventory, run  # noqa: E402
from ctsignal.sources import socrata  # noqa: E402

MILL_FIXTURE = {
    "fiscal_year": 2027, "assess_ratio": 0.70,
    "rows": [
        {"town": "Hartford", "rate": 69.95, "grand_list": 9.1e9},
        {"town": "Hamden", "rate": 53.79, "grand_list": 3.0e9},
        {"town": "New Canaan", "rate": 21.09, "grand_list": 4.0e9},
    ],
}


class TestMillRates(unittest.TestCase):
    def test_weighted_state_rate_beats_the_naive_mean(self):
        out = socrata.mill_rates({"highlight": "Hartford"},
                                 fixture=MILL_FIXTURE)
        naive = (69.95 + 53.79 + 21.09) / 3
        self.assertEqual(out["n"], 3)
        self.assertNotAlmostEqual(out["state_rate"], naive, delta=0.5)
        self.assertAlmostEqual(
            out["state_rate"],
            (69.95 * 9.1 + 53.79 * 3 + 21.09 * 4) / 16.1, places=2)
        self.assertEqual(out["median_rate"], 53.79)
        self.assertEqual(out["top"]["town"], "Hartford")
        self.assertAlmostEqual(out["top"]["multiple"],
                               69.95 / out["state_rate"], places=2)
        # the highlight is the card's own subject, not a name from config
        hart = [r for r in out["rows"] if r["state"] == "Hartford"]
        self.assertTrue(hart and hart[0]["highlight"])
        nc = [r for r in out["rows"] if r["state"] == "New Canaan"]
        self.assertTrue(nc and not nc[0]["highlight"])

    def test_empty_input_is_silence_not_crash(self):
        self.assertIsNone(socrata.mill_rates(
            {}, fixture={"fiscal_year": 2027, "rows": [],
                         "assess_ratio": 0.7}))


class TestAuditLocal(unittest.TestCase):
    """Run the audit's local eyes against the actually-generated tree:
    the committed site must have no broken links and no sitemap gaps."""

    def test_internal_links_resolve(self):
        self.assertEqual(audit.internal_links(), [])

    def test_sitemap_matches_disk(self):
        self.assertEqual(audit.sitemap_gaps(), [])


class TestInventoryArtifact(unittest.TestCase):
    def test_table_renders_without_network(self):
        path = config.ROOT / "data" / "inventory.json"
        self.assertTrue(path.exists(), "inventory artifact must be committed")
        html = inventory.table()
        self.assertIn("<table", html)
        stored = json.loads(path.read_text())
        named = [d for d in stored["datasets"] if d.get("name")]
        self.assertTrue(named)
        for d in named:
            self.assertIn(d["name"], html)


class TestFixtureMigration(unittest.TestCase):
    """A demo-triggered card must migrate onto a real headline the moment
    one is ingested — same id, same URL, real receipt."""

    def _fixture_card(self):
        from ctsignal import cards as _cards, questions as _q
        cat = {i["id"]: i for s in ("stackup", "local", "national")
               for i in _q.load_catalog()[s]}
        q = cat["quits_rate"]["question"]
        card = {"id": _cards._card_id("quits_rate", q),
                "stream": "national", "topic": "economy",
                "indicator": "quits_rate", "question": q,
                "headline": {"title": "(demo)", "source": "jobs-report "
                             "fixture (fixture)", "link": ""}}
        return cat, card

    def test_migration_replaces_demo_trigger(self):
        cat, card = self._fixture_card()
        canned = {"value": 1.9, "date": "2026-08",
                  "rows": [{"date": "2026-01", "series": "United States",
                            "value": 2.0},
                           {"date": "2026-02", "series": "United States",
                            "value": 1.9}],
                  "extreme": "lowest since January 2026",
                  "citation": "https://fred.stlouisfed.org/series/JTSQUR",
                  "query": "probe"}
        orig = run.fred.observations
        run.fred.observations = lambda item, fixture=None: dict(canned)
        try:
            cards_by_id = {card["id"]: card}
            n = run._migrate_fixtures(
                cards_by_id, cat,
                [{"id": "h1", "title": "Workers stopped quitting, and "
                  "managers noticed", "source": "NPR", "url": ""}], [])
        finally:
            run.fred.observations = orig
        self.assertEqual(n, 1)
        self.assertNotIn("(fixture)",
                         cards_by_id[card["id"]]["headline"]["source"])
        self.assertEqual(cards_by_id[card["id"]]["headline"]["source"], "NPR")

    def test_both_demo_label_styles_are_detected(self):
        from ctsignal import cards as _cards
        for src in ("jobs-report fixture", "PBS NewsHour (fixture)",
                    "CT Mirror (FIXTURE)"):
            self.assertTrue(
                _cards.is_demo_trigger(
                    {"headline": {"source": src}}), src)
        self.assertFalse(_cards.is_demo_trigger(
            {"headline": {"source": "CT Mirror"}}))

    def test_proposals_count_as_triggers_too(self):
        cat, card = self._fixture_card()
        canned = {"value": 1.9, "date": "2026-08",
                  "rows": [{"date": "2026-01", "series": "United States",
                            "value": 2.0}],
                  "extreme": "lowest on record",
                  "citation": "x", "query": "x"}
        orig = run.fred.observations
        run.fred.observations = lambda item, fixture=None: dict(canned)
        try:
            n = run._migrate_fixtures(
                {card["id"]: card}, cat, [],
                [{"indicator_id": "quits_rate",
                  "headline": {"id": "h2", "title": "The great stay put",
                               "source": "CT Mirror", "url": ""}}])
        finally:
            run.fred.observations = orig
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
