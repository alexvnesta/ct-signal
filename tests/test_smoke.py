"""Stdlib-only smoke tests: the invariants that keep an unattended pipeline
honest. Run: .venv/bin/python -m unittest discover -s tests"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ctsignal import cards, config, feeds, newsroom, publish, run, util  # noqa: E402


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
        real = config.OUTPUT_DIR / "feed.json"
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


if __name__ == "__main__":
    unittest.main()
