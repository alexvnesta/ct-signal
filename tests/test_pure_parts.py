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



class TestFailureScrub(unittest.TestCase):
    """The public failure log must never carry a credential (it once did)."""

    def test_url_scrubbed_even_without_scheme(self):
        from ctsignal.run import _scrub_failure
        msg = ("/data/2025/acs?get=NAME&key=SECRETVALUE123 broken "
               "&key=DC_API_KEY=tIA0MmsKcEZOGoWe0OsdkecxjIFjHbSs")
        out = _scrub_failure(msg)
        self.assertNotIn("tIA0Mm", out)
        self.assertNotIn("SECRETVALUE123", out)

    def test_http_url_and_length(self):
        from ctsignal.run import _scrub_failure
        out = _scrub_failure("https://x.example/a?api_key=abc " + "z" * 500)
        self.assertIn("<url>", out)
        self.assertLessEqual(len(out), 200)


class TestDcCohort(unittest.TestCase):
    """Data Commons facets age unevenly: pick the newest whole-cohort date."""

    def test_partial_newer_facet_loses_to_shared_cohort(self):
        from ctsignal.sources.datacommons import _latest_by_entity
        payload = {"byVariable": {"V": {"byEntity": {
            "a": {"observations": [
                {"date": "2026-08", "value": 5.1},
                {"date": "2026-07", "value": 5.8}]},
            "b": {"observations": [{"date": "2026-07", "value": 6.0}]},
        }}}}
        out = _latest_by_entity(payload, "V")
        self.assertEqual(out["a"], ("2026-07", 5.8))
        self.assertEqual(out["b"], ("2026-07", 6.0))

class TestAuditLocal(unittest.TestCase):
    """Run the audit's local eyes against the actually-generated tree:
    the committed site must have no broken links and no sitemap gaps."""

    def test_internal_links_resolve(self):
        self.assertEqual(audit.internal_links(), [])

    def test_sitemap_matches_disk(self):
        self.assertEqual(audit.sitemap_gaps(), [])

    def test_ask_desk_and_five_numbers_ship(self):
        """The promises from the round-3 review, asserted in the built
        artifact so a template edit that quietly drops either fails the
        cycle: an ask surface on every page, a five-number town brief."""
        page = (config.ROOT / "index.html").read_text()
        tpage = (config.ROOT / "towns.html").read_text()
        self.assertIn("Ask the desk a question", page)
        self.assertIn("subject=Question%20for%20the%20desk", page)
        for metric in ("income", "poverty", "rent", "value", "age"):
            self.assertIn(f'fmt("{metric}"', tpage.replace("'", '"'),
                          f"town brief must render {metric} (towns page)")

    def test_town_feed_is_valid_atom(self):
        """A feed is a promise to machines: wrong vocabulary parses but
        starves readers. The advertised (Atom) format must be the one in
        the file: namespaced entries, RFC-3339 stamps, no RSS fossils."""
        import re as _re
        import xml.etree.ElementTree as ET
        raw = (config.ROOT / "town" / "greenwich" / "feed.xml").read_text()
        self.assertNotIn("<item>", raw)
        root = ET.fromstring(raw)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = root.findall("a:entry", ns)
        self.assertGreaterEqual(len(entries), 1)
        for e in entries:
            self.assertTrue(e.findtext("a:id", namespaces=ns))
            self.assertEqual(
                _re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                          e.findtext("a:updated", namespaces=ns) or "")
                is not None, True,
                "Atom updated must be RFC-3339")
        feed_updated = root.findtext("a:updated", namespaces=ns)
        newest = max(e.findtext("a:updated", namespaces=ns)
                     for e in entries)
        self.assertEqual(feed_updated, newest)


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

    def test_no_trigger_files_the_card_not_demos_it(self):
        """The override the standing bar allows: when no real headline
        exists, the synthetic trigger is DELETED, not displayed. The
        card keeps its live numbers and claims only what it can show."""
        from ctsignal import cards as _cards
        cat, card = self._fixture_card()
        orig = run.fred.observations
        run.fred.observations = lambda item, fixture=None: None
        try:
            cards_by_id = {card["id"]: card}
            n = run._migrate_fixtures(cards_by_id, cat, [], [])
        finally:
            run.fred.observations = orig
        c = cards_by_id[card["id"]]
        self.assertEqual(n, 1)
        self.assertIsNone(c.get("headline"))
        self.assertEqual(c.get("origin"), "data desk")
        self.assertFalse(_cards.is_demo_trigger(c))

    def test_filed_card_numbers_do_not_fossilize(self):
        """A filed card is a standing question: each cycle revalidates
        its numbers without re-aging the story or losing its origin."""
        cat, card = self._fixture_card()
        card.pop("headline")
        card["origin"] = "data desk"
        card["generated_at"] = "2026-10-01T00:00:00+00:00"
        card["answer_text"] = "old answer"
        canned = {"value": 2.4, "date": "2026-09",
                  "rows": [{"date": "2026-08", "series": "United States",
                            "value": 2.5},
                           {"date": "2026-09", "series": "United States",
                            "value": 2.4}],
                  "extreme": "lowest since January 2026",
                  "citation": "https://fred.stlouisfed.org/series/JTSQUR",
                  "query": "probe"}
        orig = run.fred.observations
        run.fred.observations = lambda item, fixture=None: dict(canned)
        try:
            cards_by_id = {card["id"]: card}
            n = run._migrate_fixtures(cards_by_id, cat, [], [])
        finally:
            run.fred.observations = orig
        c = cards_by_id[card["id"]]
        self.assertEqual(n, 1)
        self.assertNotEqual(c["answer_text"], "old answer")
        self.assertEqual(c["generated_at"], "2026-10-01T00:00:00+00:00")
        self.assertIn("revalidated_at", c)
        self.assertEqual(c["origin"], "data desk")

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


def _cards_questions():
    from ctsignal import questions as _q
    cat = _q.load_catalog()
    return cat["stackup"] + cat["local"] + cat["national"]


class TestTriggerQuality(unittest.TestCase):
    """The promotion gate: a receipt must mean the story raised the
    question, not merely contain a phrase. Both paths — new cards and
    promotion — must share one bar so they can never drift."""

    def test_weak_single_phrase_is_blocked(self):
        from ctsignal import questions as _q
        self.assertFalse(_q._strong_enough(["workforce"]))
        self.assertFalse(_q._strong_enough(["hiring"]))
        self.assertFalse(_q._strong_enough(["labor market"]))
        self.assertFalse(_q._strong_enough(["town council"]))

    def test_specific_phrase_alone_passes(self):
        from ctsignal import questions as _q
        self.assertTrue(_q._strong_enough(["jobless claims"]))
        self.assertTrue(_q._strong_enough(["workforce reduction"]))

    def test_two_weak_phrases_pass(self):
        from ctsignal import questions as _q
        self.assertTrue(_q._strong_enough(["labor market", "workforce"]))

    def test_proposer_uses_the_same_bar(self):
        """A civil-rights story with one generic word must not open a
        labor card — this exact headline produced one in production."""
        from ctsignal import questions as _q
        cat = _q.load_catalog()
        headline = {"id": "h-test", "title": "Reshaped civil rights "
                    "mission at Justice Department transforms its work, "
                    "workforce", "url": "", "source": "NPR",
                    "published": "2026-10-11", "published_sort": 0}
        proposals = _q.propose_from_catalog(headline, cat, "stackup")
        ids = {p["indicator_id"] for p in proposals}
        self.assertNotIn("prime_age_participation", ids)

    def test_political_heat_does_not_open_the_weather_card(self):
        """'Heat' in a Senate-race story once minted the weather card.
        A metaphor is not a weather receipt; 'heat wave' still is."""
        from ctsignal import questions as _q
        cat = _q.load_catalog()
        political = {"id": "h-heat", "title": "In Michigan, El-Sayed Faces "
                     "Heat From Former Primary Rival as Election Nears",
                     "url": "", "source": "NYT U.S.",
                     "published": "2026-10-28", "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(political, cat, "stackup")}
        self.assertNotIn("weather_anomaly", ids)

        weather = {"id": "h-hw", "title": "Heat wave grips Connecticut",
                   "url": "", "source": "NBC Connecticut",
                   "published": "2026-10-28", "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(weather, cat, "stackup")}
        self.assertIn("weather_anomaly", ids)

    def test_single_person_quits_does_not_open_the_quits_card(self):
        """A rail chief 'Quits' is a person leaving a job, not a population
        quits rate; the same ambiguity once promoted the card."""
        from ctsignal import questions as _q
        cat = _q.load_catalog()
        person = {"id": "h-q", "title": "California's High-Speed Rail Chief "
                  "Quits Amid Questions About Spending", "url": "",
                  "source": "NYT U.S.", "published": "2026-10-29",
                  "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(person, cat, "stackup")}
        self.assertNotIn("quits_rate", ids)

        coach = {"id": "h-c", "title": "Connecticut high school football "
                 "coach quits mid-game after confrontation", "url": "",
                 "source": "Google News (CT)", "published": "2026-10-29",
                 "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(coach, cat, "stackup")}
        self.assertNotIn("quits_rate", ids)

        population = {"id": "h-p", "title": "Americans quit their jobs at "
                      "the lowest rate on record", "url": "",
                      "source": "NPR", "published": "2026-10-29",
                      "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(population, cat, "stackup")}
        self.assertIn("quits_rate", ids)

    def test_generic_storm_does_not_open_the_weather_card(self):
        """A remote Alaska storm story has no bearing on Connecticut's
        30-day temperature anomaly; a storm that names CT's weather does."""
        from ctsignal import questions as _q
        cat = _q.load_catalog()
        remote = {"id": "h-st", "title": "After last year's storm, this "
                  "remote Alaska town is still picking up the pieces",
                  "url": "", "source": "NYT U.S.", "published": "2026-10-30",
                  "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(remote, cat, "stackup")}
        self.assertNotIn("weather_anomaly", ids)

        named = {"id": "h-st2", "title": "'Big' Storm To Impact CT's "
                 "Weather: Here's What To Know - Patch", "url": "",
                 "source": "Google News (CT)", "published": "2026-10-30",
                 "published_sort": 0}
        ids = {p["indicator_id"] for p in
               _q.propose_from_catalog(named, cat, "local")}
        self.assertIn("weather_anomaly", ids)

    def test_migration_promotion_respects_the_bar(self):
        """The hiring-editor headline must not promote the hires card."""
        from ctsignal import cards as _cards
        cat = {i["id"]: i for sec in ("stackup", "local", "national")
               for i in _cards_questions()}
        q = cat["hires_rate"]["question"]
        card = {"id": _cards._card_id("hires_rate", q),
                "stream": "national", "topic": "economy",
                "indicator": "hires_rate", "question": q,
                "headline": {"title": "(demo)", "source": "jobs-report "
                             "fixture (fixture)", "link": ""}}
        orig = run.fred.observations
        seen = {}
        def fake(item, fixture=None):
            seen["called"] = True
            return {"value": 1.9, "date": "2026-08",
                    "rows": [{"date": "2026-01", "series": "United States",
                              "value": 2.0}],
                    "extreme": "lowest since January 2026",
                    "citation": "https://fred.stlouisfed.org/series/JTSQUR",
                    "query": "probe"}
        run.fred.observations = fake
        try:
            cards_by_id = {card["id"]: card}
            n = run._migrate_fixtures(
                cards_by_id, cat,
                [{"id": "h1", "title": "CT Mirror launches arts and "
                  "culture coverage, hires Lucy Gellman as editor",
                  "source": "CT Mirror", "url": ""}], [])
        finally:
            run.fred.observations = orig
        self.assertEqual(n, 1)
        self.assertEqual(seen, {})
        self.assertIsNone(cards_by_id[card["id"]].get("headline"))
        self.assertEqual(cards_by_id[card["id"]].get("origin"), "data desk")

class TestWeatherAnswerer(unittest.TestCase):
    """The ACIS weather card: signed anomaly arithmetic, never a mood,
    and never a degree sign doubled."""

    def test_signed_answer_formats(self):
        from ctsignal import run as _r, questions as _q
        cat = _q.load_catalog()
        item = next(i for i in cat["national"]
                    if i["id"] == "weather_anomaly")
        canned = {"value": 1.1, "date": "2026-10-13", "stations": ["KBDL"],
                  "precip": 4.5, "precip_normal": 4.6,
                  "rows": [{"date": "2026-10-13", "series": "Bradley Intl",
                            "value": 1.1}],
                  "extreme": "warmer than normal",
                  "citation": "https://data.rcc-acis.org/StnData",
                  "query": "probe", "cache": False}
        orig = _r.acis.observations
        _r.acis.observations = lambda: dict(canned)
        try:
            card = _r._answer_national(
                {"headline": {"id": "h-w", "title": "t", "url": "",
                              "source": "s", "published": "",
                              "published_sort": 0}}, item)
        finally:
            _r.acis.observations = orig
        self.assertIn("+1.1\u00b0F", card["answer_text"])
        self.assertNotIn("\u00b0F\u00b0F", card["answer_text"])
        self.assertIn("warmer than normal", card["answer_text"])

    def test_negative_anomaly_reads_cooler(self):
        from ctsignal import run as _r, questions as _q
        cat = _q.load_catalog()
        item = next(i for i in cat["national"]
                    if i["id"] == "weather_anomaly")
        canned = {"value": -2.4, "date": "2026-01-10", "stations": ["KBDL"],
                  "precip": 1.0, "precip_normal": 3.0,
                  "rows": [{"date": "2026-01-10", "series": "Bradley Intl",
                            "value": -2.4}],
                  "extreme": "", "citation": "c", "query": "q",
                  "cache": False}
        orig = _r.acis.observations
        _r.acis.observations = lambda: dict(canned)
        try:
            card = _r._answer_national(
                {"headline": {"id": "h-w", "title": "t", "url": "",
                              "source": "s", "published": "",
                              "published_sort": 0}}, item)
        finally:
            _r.acis.observations = orig
        self.assertIn("-2.4\u00b0F", card["answer_text"])
        self.assertIn("cooler than normal", card["answer_text"])
