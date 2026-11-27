"""UX, visual, and editorial regression guards.

Pins the high-leverage visual and usability invariants established during the
2026-11-27 UX polish pass so future automated or agentic edits cannot silently
regress them. Run: .venv/bin/python -m unittest discover -s tests
"""
import importlib.util
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctsignal import charts, config, newsroom, publish, questions, share, theme  # noqa: E402


def _load_make_story_covers():
    spec = importlib.util.spec_from_file_location(
        "make_story_covers", ROOT / "scripts" / "make_story_covers.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestThumbnailFormatting(unittest.TestCase):
    def setUp(self):
        self.msc = _load_make_story_covers()

    def test_weather_warmer_keeps_sign_and_unit(self):
        card = {
            "stream": "national",
            "answer_text": "Connecticut ran 4.6°F warmer than normal over the "
                           "30 days ending 2026-11-26 — measured at Bradley.",
            "answer_values": {"value": 4.6, "date": "2026-11-26"},
        }
        self.assertEqual(self.msc._thumb_value(card), "+4.6°F")

    def test_weather_cooler_keeps_minus_and_unit(self):
        card = {
            "stream": "national",
            "answer_text": "Connecticut ran 2.4°F cooler than normal over the "
                           "30 days ending 2026-01-10.",
            "answer_values": {"value": -2.4, "date": "2026-01-10"},
        }
        self.assertEqual(self.msc._thumb_value(card), "-2.4°F")

    def test_violent_crime_carries_per_100k_unit(self):
        card = {
            "stream": "stackup",
            "answer_text": "Connecticut reports 147 violent crimes per 100k "
                           "people (2023), the 3rd-lowest reported of 52 peers.",
            "answer_values": {"value": 147, "date": "2023"},
        }
        self.assertEqual(self.msc._thumb_value(card), "147/100k")


class TestChartUX(unittest.TestCase):
    TOP10 = [
        {"state": "Hartford", "value": 69.95, "rank": 1, "highlight": True},
        {"state": "Hamden", "value": 53.67, "rank": 2, "highlight": False},
        {"state": "Waterbury", "value": 42.98, "rank": 3, "highlight": False},
    ]

    def test_rank_strip_sorts_rank_one_at_top_with_top_level_data(self):
        spec = charts.rank_strip(
            self.TOP10, title="Property tax rate, FY2027 (top 10 towns)",
            unit="mills per $1,000", peer_word="Town",
        )
        self.assertIn("data", spec)
        self.assertEqual(len(spec["data"]["values"]), 3)
        self.assertIn("layer", spec)
        bar_layer = spec["layer"][0]
        self.assertEqual(bar_layer["encoding"]["y"]["sort"][0], "Hartford")
        # X-axis title carries unit only, never repeating the chart title
        self.assertEqual(bar_layer["encoding"]["x"]["title"], "mills per $1,000")
        # Headroom beyond top value so bar + label never slam into right edge
        dom = bar_layer["encoding"]["x"]["scale"]["domain"]
        self.assertGreater(dom[1], 69.95 * 1.1)

    def test_dark_share_export_repaints_bar_end_labels(self):
        spec = charts.rank_strip(
            self.TOP10, title="Property tax rate", unit="mills per $1,000",
        )
        dark = share._export_spec(spec)
        text_layer = dark["layer"][1]
        rng = text_layer["encoding"]["color"]["scale"]["range"]
        self.assertIn(share.SHARE_INK, rng)
        self.assertNotIn("#1c2733", rng)


class TestEditorialAndLayoutUX(unittest.TestCase):
    def test_board_kpi_values_use_neutral_ink_not_green(self):
        m = re.search(r"\.val\{[^}]+\}", theme.CSS)
        self.assertIsNotNone(m)
        self.assertIn("color:var(--ink)", m.group(0))
        self.assertNotIn("color:var(--ok)", m.group(0))

    def test_rail_resets_top_margin_and_wire_uses_grid(self):
        self.assertIn(".rail{margin-top:0", theme.CSS)
        self.assertIn("display:grid;grid-template-columns:repeat(2", theme.CSS)
        self.assertNotIn("column-count:2", theme.CSS)

    def test_header_marks_active_section_and_includes_indicators(self):
        h = theme.header(compact=True, active_path="/town/hartford")
        self.assertIn('href="/towns" aria-current="page"', h)
        self.assertIn('href="/indicators">Indicators</a>', h)
        h_ind = theme.header(compact=True, active_path="/indicator/median_rent")
        self.assertIn('href="/indicators" aria-current="page"', h_ind)

    def test_story_lede_does_not_echo_finding_verbatim(self):
        card = {
            "question": "Which Connecticut town has the highest property tax rate?",
            "answer_text": "In fiscal year 2027, Hartford taxes real property "
                           "at 69.95 mills, 2.6 times the 26.65-mill rate that "
                           "property pays statewide across 169 towns.",
        }
        finding = newsroom._finding(card)
        lede = newsroom._story_lede(card)
        self.assertFalse(lede.startswith(finding))
        self.assertIn("2.6 times", lede)

    def test_homepage_caption_does_not_say_below(self):
        cards = json.loads(
            (config.OUTPUT_DIR / "cards.json").read_text()
        )["cards"]
        desc_home, _ = newsroom.chart_intro(cards[0], on_home=True)
        self.assertIn("on the story page", desc_home)
        self.assertNotIn("Source and query below.", desc_home)

    def test_wire_filter_blocks_sports_blotter_and_false_shooting_match(self):
        self.assertFalse(questions._strong_enough(["shooting"]))
        self.assertFalse(questions.wire_worthy({
            "stream": "national",
            "title": "After Deadly Bondi Beach Shooting, Two Non-Jews Marry Under a Huppah",
        }, has_data=True))
        self.assertFalse(questions.wire_worthy({
            "stream": "ct",
            "title": "Who is playing in the girls soccer Senior Bowl on Sunday? - Stamford Advocate",
        }, has_data=False))
        self.assertFalse(questions.wire_worthy({
            "stream": "ct",
            "title": "NY man accused of sneaking into bedroom of 14-year-old girl in CT",
        }, has_data=False))
        self.assertTrue(questions.wire_worthy({
            "stream": "ct",
            "title": "CT looks to next steps after ruling on ICE",
        }, has_data=False))

    def test_touch_targets_meet_44px_minimum(self):
        vote_rule = re.search(r"\.vote button\{[^}]+\}", theme.CSS)
        self.assertIsNotNone(vote_rule)
        self.assertIn("min-height:44px", vote_rule.group(0))
        act_rule = re.search(r"\.chart-actions a,\.chart-actions button\{[^}]+\}", theme.CSS)
        self.assertIsNotNone(act_rule)
        self.assertIn("min-height:44px", act_rule.group(0))

    def test_disclosure_chevron_css_escape_is_intact(self):
        self.assertIn(r'content:"\25b8"', theme.CSS)
        self.assertNotIn("\x15b8", theme.CSS)

    def test_deploy_script_tracks_all_generated_paths(self):
        deploy = (ROOT / "deploy.sh").read_text()
        for path in ("indicator", "indicators", "towns.csv", "privacy.html"):
            self.assertIn(path, deploy)


if __name__ == "__main__":
    unittest.main()
