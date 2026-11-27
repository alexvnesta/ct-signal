"""Unit and build tests for CT Signal growth features:
  - New live CT Socrata adapters (housing_permits, home_sales, fiscal_metric)
  - Town interactive Property Tax Estimator & 1-click Copy Summary bar
  - Side-by-side /compare tool & enriched 169-town payload
  - /week/ web brief archive + issue pages
  - /partner page + honest cookieless Vercel Web Analytics disclosure
  - Bluesky material-change weather gate & cross-desk rotation
  - Weekly multi-channel distribution draft generator
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ctsignal import cards, config, questions, theme  # noqa: E402
from ctsignal.sources import socrata  # noqa: E402
import make_story_covers  # noqa: E402
import select_bsky_posts  # noqa: E402
import weekly_social_draft  # noqa: E402


class TestNewCtAdapters(unittest.TestCase):
    def test_housing_permits_excludes_state_total_and_ranks_descending(self):
        fx = {
            "latest_year": 2025,
            "prior_year": 2024,
            "rows": [
                {"town": "Connecticut", "value": 9834, "prior": 8100},
                {"town": "New Haven", "value": 829, "prior": 600},
                {"town": "Stamford", "value": 1564, "prior": 1200},
            ],
        }
        res = socrata.housing_permits({"socrata_id": "stm9-38x4"}, fixture=fx)
        self.assertIsNotNone(res)
        self.assertEqual(res["n"], 2)
        self.assertEqual(res["top"]["town"], "Stamford")
        self.assertEqual(res["state_value"], 2393)
        item = {
            "id": "housing_permits", "topic": "housing", "socrata_id": "stm9-38x4",
            "unit": "units", "chart_label": "New housing units permitted",
            "question": "Which Connecticut towns permitted the most new housing?",
            "answer": "{top_town} permitted {value} new housing units in {latest_year}, leading {n} Connecticut towns ({state} units permitted statewide).",
        }
        card = cards.from_local_rank(item, {"headline": None}, res)
        self.assertIn("Stamford permitted 1,564", card["answer_text"])
        self.assertEqual(len(card["towns"]), 2)

    def test_home_sales_filters_small_sample_towns(self):
        fx = {
            "latest_year": 2024,
            "state_value": 426000,
            "total_sales": 29507,
            "rows": [
                {"town": "Union", "value": 900000, "sales": 3},
                {"town": "Greenwich", "value": 2850000, "sales": 607},
                {"town": "Hartford", "value": 260000, "sales": 277},
            ],
        }
        res = socrata.home_sales({"socrata_id": "5mzw-sjtu", "min_sales": 10}, fixture=fx)
        self.assertEqual(res["n"], 2)
        self.assertEqual(res["top"]["town"], "Greenwich")
        self.assertEqual([r["town"] for r in res["all"]], ["Greenwich", "Hartford"])

    def test_fiscal_metric_normalizes_all_caps_towns(self):
        fx = {
            "latest_year": 2023,
            "edition": "Report Edition: 2019-2023",
            "rows": [
                {"town": "EAST HARTFORD", "value": 16435.5},
                {"town": "SHARON", "value": 47845.3},
                {"town": "Total", "value": 20000},
            ],
        }
        res = socrata.fiscal_metric(
            {"socrata_id": "xgef-f6jp", "metric": "Net current education expenditures per pupil (CSDE)"},
            fixture=fx,
        )
        self.assertEqual(res["n"], 2)
        self.assertEqual(res["top"]["town"], "Sharon")
        self.assertEqual(res["all"][1]["town"], "East Hartford")

    def test_thumb_value_formats_millions_dollars_units_and_kwh(self):
        self.assertEqual(make_story_covers._thumb_value({
            "stream": "local",
            "answer_text": "Single-family homes in Greenwich sold for a median of $2,850,000 in 2024.",
            "answer_values": {"top": {"town": "Greenwich", "value": 2850000}},
        }), "$2.85M")
        self.assertEqual(make_story_covers._thumb_value({
            "stream": "local",
            "answer_text": "Sharon spent $47,845 per public school student in 2023.",
            "answer_values": {"top": {"town": "Sharon", "value": 47845}},
        }), "$47,845")
        self.assertEqual(make_story_covers._thumb_value({
            "stream": "local",
            "answer_text": "Stamford permitted 1,564 new housing units in 2025.",
            "answer_values": {"top": {"town": "Stamford", "value": 1564}},
        }), "1,564")
        self.assertEqual(make_story_covers._thumb_value({
            "stream": "national",
            "answer_text": "Northeast urban electricity averaged $0.266 per kWh in 2026-10.",
            "answer_values": {"value": 0.266},
        }), "$0.266")


class TestBskySelectionAndWeeklyDraft(unittest.TestCase):
    def test_weather_material_change_gate_and_desk_rotation(self):
        prev = [
            {"id": "w1", "topic": "weather", "stream": "national", "answer_values": {"date": "2026-11-26", "value": 4.6}},
            {"id": "l1", "topic": "housing", "stream": "local", "answer_values": {"date": "2024", "value": 100}},
        ]
        # 5.2°F is >=5.0 but moved only +0.6°F from 4.6 -> blocked!
        cur_small_delta = [
            {"id": "w1", "topic": "weather", "stream": "national", "answer_values": {"date": "2026-11-27", "value": 5.2}},
        ]
        self.assertEqual(select_bsky_posts.select_candidates(cur_small_delta, prev), [])

        # +6.5°F moved +1.9°F from 4.6 -> passes unless weather cooldown active
        cur_big_jump = [
            {"id": "w1", "topic": "weather", "stream": "national", "answer_values": {"date": "2026-11-27", "value": 6.5}},
            {"id": "h1", "topic": "housing", "stream": "local", "answer_values": {"date": "2025", "value": 1564}},
            {"id": "h2", "topic": "housing", "stream": "local", "answer_values": {"date": "2024", "value": 2850000}},
            {"id": "e1", "topic": "local-finance", "stream": "local", "answer_values": {"date": "2023", "value": 47845}},
        ]
        # When last_topic was housing, local-finance rotates first and only 1 per topic is picked
        picked = select_bsky_posts.select_candidates(
            cur_big_jump, prev, last_topic="housing", recent_weather=True, limit=2)
        self.assertEqual([c["id"] for c in picked], ["e1", "h1"])
        self.assertNotIn("w1", [c["id"] for c in picked])

    def test_weekly_social_draft_has_all_four_channels_and_bsky_cap(self):
        cards_data = json.loads((ROOT / "output" / "cards.json").read_text())["cards"]
        board = json.loads((ROOT / "board.json").read_text())
        md = weekly_social_draft.render_draft(cards_data, board)
        for heading in ("## 1. LinkedIn", "## 2. r/Connecticut",
                        "## 3. Local Facebook Town Group / Nextdoor",
                        "## 4. Bluesky Weekly Thread"):
            self.assertIn(heading, md)
        self.assertIn("/compare", md)
        self.assertIn("/week/", md)


class TestBuiltGrowthSurfaces(unittest.TestCase):
    def test_town_pages_carry_tax_estimator_share_bar_and_new_datasets(self):
        hartford = (ROOT / "town" / "hartford" / "index.html").read_text()
        self.assertIn('id="tax-estimator"', hartford)
        self.assertIn('id="copy-town-sum"', hartford)
        self.assertIn('href="/compare?a=hartford"', hartford)
        self.assertIn("Single-family home sales", hartford)
        self.assertIn("New housing permits", hartford)
        self.assertIn("Public school spending", hartford)

    def test_compare_page_and_routes_wired(self):
        cmp_html = (ROOT / "compare.html").read_text()
        self.assertIn("Compare Connecticut towns", cmp_html)
        self.assertIn("window.__CMP__=", cmp_html)
        self.assertIn('"mill":', cmp_html)
        self.assertIn('"sale":', cmp_html)
        self.assertIn('"school":', cmp_html)
        self.assertIn('"permits":', cmp_html)
        self.assertIn(f"{config.SITE_URL}/compare</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("compare", (ROOT / "vercel.json").read_text())
        self.assertIn("compare.html", (ROOT / "deploy.sh").read_text())

    def test_week_archive_and_issues_built_and_in_sitemap(self):
        idx = (ROOT / "week" / "index.html").read_text()
        self.assertIn("What moved in Connecticut data", idx)
        self.assertIn("/week/2026-W48", idx)
        w48 = (ROOT / "week" / "2026-W48" / "index.html").read_text()
        self.assertIn("Weekly brief", w48)
        self.assertIn("Connecticut board snapshot", w48)
        sm = (ROOT / "sitemap.xml").read_text()
        self.assertIn(f"{config.SITE_URL}/week</loc>", sm)
        self.assertIn(f"{config.SITE_URL}/week/2026-W48</loc>", sm)
        self.assertIn(" week", (ROOT / "deploy.sh").read_text())

    def test_partner_page_and_analytics_disclosure(self):
        partner = (ROOT / "partner.html").read_text()
        self.assertIn("Partner &amp; underwrite", partner)
        self.assertIn("Editorial firewall", partner)
        self.assertIn(f"{config.SITE_URL}/partner</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("/_vercel/insights/script.js", theme.SPEED_INSIGHTS)
        self.assertIn("ctsignal\\.org", theme.SPEED_INSIGHTS)
        privacy = (ROOT / "privacy.html").read_text()
        self.assertIn("Vercel Web Analytics", privacy)


class TestEditorialCleanups(unittest.TestCase):
    def test_trigger_worthy_rejects_off_geo_and_noise_allows_ct(self):
        self.assertFalse(questions.trigger_worthy({
            "stream": "national",
            "title": "After Deadly Bondi Beach Shooting, Two Non-Jews Marry Under a Huppah",
        }))
        self.assertFalse(questions.trigger_worthy({
            "stream": "national",
            "title": "Why Chicago’s Tax Incentive Program Fell Short in Low-Income Neighborhoods",
        }))
        self.assertFalse(questions.trigger_worthy({
            "stream": "national",
            "title": "Harvard Endowment Soars to $68 Billion Even as Federal Cuts Force Layoffs",
        }))
        self.assertTrue(questions.trigger_worthy({
            "stream": "ct",
            "title": "Lamont: CT’s savings habits pay big dividends in next budget",
        }))
        self.assertTrue(questions.trigger_worthy({
            "stream": "national",
            "title": "U.S. inflation report highlights strain of rising food, energy and housing costs",
        }))

    def test_no_live_card_carries_off_topic_legacy_trigger(self):
        cards_data = json.loads((ROOT / "output" / "cards.json").read_text())["cards"]
        for c in cards_data:
            title = str((c.get("headline") or {}).get("title") or "").lower()
            for bad in ("bondi beach", "chicago", "harvard endowment"):
                self.assertNotIn(bad, title, f"stale off-topic trigger on {c['id']}")

    def test_unemployment_board_and_story_agree_on_bls_rate(self):
        board = json.loads((ROOT / "board.json").read_text())
        cards_data = json.loads((ROOT / "output" / "cards.json").read_text())["cards"]
        tile = next(t for t in board["tiles"] if t["id"] == "unemployment")
        by_ind = {c.get("indicator"): c for c in cards_data}
        st_card = by_ind["unemployment"]
        ct_card = by_ind["ct_unemployment"]
        self.assertEqual(tile["date"], st_card["answer_values"]["date"])
        self.assertEqual(tile["date"], ct_card["answer_values"]["date"])
        self.assertEqual(st_card["answer_values"]["value"], ct_card["answer_values"]["value"])

    def test_front_page_excludes_us_only_macro_cards(self):
        cards_data = json.loads((ROOT / "output" / "cards.json").read_text())["cards"]
        us_only_ids = {
            c["id"] for c in cards_data
            if c.get("stream") == "national"
            and c.get("indicator") not in ("weather_anomaly", "ct_unemployment", "northeast_electricity")
        }
        home = (ROOT / "index.html").read_text()
        for cid in us_only_ids:
            self.assertNotIn(f'/story/{cid}"', home, f"US-only macro card {cid} leaked onto CT front page")

    def test_weekly_draft_leads_with_computed_spreads_and_shares(self):
        cards_data = json.loads((ROOT / "output" / "cards.json").read_text())["cards"]
        board = json.loads((ROOT / "board.json").read_text())
        md = weekly_social_draft.render_draft(cards_data, board)
        self.assertIn("% of all new housing in Connecticut", md)
        self.assertIn("Greenwich", md)
        self.assertIn("Stamford", md)
        self.assertIn("Hartford", md)


if __name__ == "__main__":
    unittest.main()
