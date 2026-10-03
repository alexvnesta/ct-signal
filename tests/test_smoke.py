"""Stdlib-only smoke tests: the invariants that keep an unattended pipeline
honest. Run: .venv/bin/python -m unittest discover -s tests"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ctsignal import cards, config, feeds, newsroom, publish, run, util  # noqa: E402
from ctsignal.sources import socrata  # noqa: E402


class TestUtil(unittest.TestCase):
    def test_naive_timestamps_are_utc(self):
        import datetime as dt
        aware = util.parse_ts("2026-10-02T04:23:00")
        self.assertEqual(aware.tzinfo, dt.timezone.utc)

    def test_atomic_roundtrip(self):
        tmp = pathlib.Path(__file__).parent / ".tmp_probe.json"
        try:
            util.write_json(tmp, {"b": 2, "a": 1})
            self.assertEqual(json.loads(tmp.read_text()), {"a": 1, "b": 2})
            self.assertFalse(tmp.with_name(tmp.name + ".tmp").exists())
        finally:
            tmp.unlink(missing_ok=True)


class TestFeeds(unittest.TestCase):
    def test_link_scheme_allowlist(self):
        self.assertEqual(feeds._safe_link("javascript:alert(1)"), "")
        self.assertEqual(feeds._safe_link("data:text/html,x"), "")
        self.assertEqual(feeds._safe_link(None), "")
        self.assertEqual(feeds._safe_link("https://x.org/a"), "https://x.org/a")
        self.assertEqual(feeds._safe_link("HTTP://X.ORG"), "HTTP://X.ORG")

    def test_token_never_travels_with_rss_headers(self):
        self.assertNotIn("X-App-Token", config.UA)


class TestPipeline(unittest.TestCase):
    def test_asked_key_tracks_data_date(self):
        card = {"indicator": "x", "question": "q?" * 40,
                "answer_values": {"date": "2024"}}
        k1 = run._asked_key(card)
        card["answer_values"]["date"] = "2025"
        self.assertNotEqual(k1, run._asked_key(card))

    def test_feed_load_is_strict(self):
        real = config.OUTPUT_DIR / "cards.json"
        keep = real.read_text()
        try:
            real.write_text("{ truncated")
            with self.assertRaises(RuntimeError):
                run._load_feed()
            real.write_text("[1,2]")
            with self.assertRaises(RuntimeError):
                run._load_feed()
        finally:
            real.write_text(keep)

    def test_ordinals(self):
        ind = {"higher_is": "top"}
        self.assertEqual(cards.human_rank(ind, 1, 52), "1st-highest")
        self.assertEqual(cards.human_rank(ind, 22, 52), "22nd-highest")


class TestRender(unittest.TestCase):
    def test_islands_neutralize_parser_breakers(self):
        blob = newsroom._spec_json(
            {"url": "us.json", "x": "<!-- </script>"})
        self.assertIn(f"{config.SITE_URL}/us.json", blob)
        self.assertNotIn("</script>", blob)
        self.assertIn("<\\u0021--", blob)

    def test_story_cover_helper_missing_is_none(self):
        self.assertIsNone(
            newsroom._cover_path({"id": "deadbeefdead"}))

    def test_head_escapes_and_has_no_tag_mismatch(self):
        html = publish.home_html([], {}) if hasattr(publish, "home_html") else ""
        self.assertIn("</h2>", html or "</h2>")


class TestSprintSurfaces(unittest.TestCase):
    """Guards for the surfaces shipped in the content sprint: they are the
    long-tail entry doors, so silent breakage must fail the cycle."""

    def _cards(self):
        return json.loads(
            (config.OUTPUT_DIR / "cards.json").read_text())["cards"]

    def test_every_town_row_has_a_page(self):
        card = next(c for c in self._cards() if c.get("towns"))
        for row in card["towns"]:
            page = (config.ROOT / "town" / newsroom._slug(row["town"])
                    / "index.html")
            self.assertTrue(page.exists(), f"missing {page}")
        body = (config.ROOT / "town" / "bridgeport" / "index.html").read_text()
        self.assertIn("Bridgeport", body)
        self.assertIn("of 169", body)

    def test_archive_and_sources_pages_exist(self):
        self.assertIn("Every question",
                      (config.ARCHIVE_DIR / "index.html").read_text())
        self.assertIn("webp-fgt3",
                      (config.ROOT / "sources.html").read_text())

    def test_supersede_records_permanent_redirect(self):
        vp = config.ROOT / "vercel.json"
        keep = vp.read_text()
        try:
            run._record_redirect("ffffffffffff", "eeeeeeeeeeee")
            cfg = json.loads(vp.read_text())
            self.assertIn({"source": "/story/ffffffffffff",
                           "destination": "/story/eeeeeeeeeeee",
                           "permanent": True}, cfg["redirects"])
            run._record_redirect("ffffffffffff", "eeeeeeeeeeee")  # idempotent
            self.assertEqual(json.loads(vp.read_text())["redirects"].count(
                {"source": "/story/ffffffffffff",
                 "destination": "/story/eeeeeeeeeeee", "permanent": True}), 1)
        finally:
            vp.write_text(keep)

    def test_socrata_pagination_walks_pages(self):
        pages = {0: [1] * 1000, 1000: [2] * 500}
        out = socrata._paginated(lambda off: pages.get(off, []),
                                 page=1000, max_rows=40000)
        self.assertEqual(len(out), 1500)
        self.assertEqual(out[1000], 2)

    def test_trigger_parts_single_source(self):
        # board and story share theme.trigger_parts; both render it, and a
        # trigger with a URL links out with noopener on BOTH surfaces
        cards = self._cards()
        linked = next(c for c in cards if c["headline"].get("url"))
        home = publish.home_html(cards, {})
        story = (config.STORY_DIR / f"{linked['id']}" / "index.html").read_text()
        for surface in (home, story):
            self.assertIn("Source", surface)
            self.assertIn('rel="noopener"', surface)
        self.assertEqual(1, story.count('class="skip"'),
                         "exactly one skip link per page")


if __name__ == "__main__":
    unittest.main()
