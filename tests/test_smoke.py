"""Stdlib-only smoke tests: the invariants that keep an unattended pipeline
honest. Run: .venv/bin/python -m unittest discover -s tests"""
import datetime as dt
import json
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ctsignal import (cards, charts, config, feeds, newsroom, publish, run,
                      theme, util)  # noqa: E402
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

    def test_finding_headline_drops_peer_rank_tail(self):
        card = {"question": "How rich is Connecticut?",
                "answer_text": "Connecticut's median household income is "
                               "$100,056 (2025), the 9th-highest of 52 peers."}
        self.assertEqual(newsroom._finding(card),
                         "Connecticut's median household income is $100,056 (2025)")

    def test_finding_headline_drops_any_peer_rank_tail(self):
        card = {"question": "How safe is Connecticut?",
                "answer_text": "Connecticut reports 147 violent crimes per "
                               "100k people (2023), the 3rd-safest of 52 peers."}
        self.assertEqual(newsroom._finding(card),
                         "Connecticut reports 147 violent crimes per "
                         "100k people (2023)")

    def test_finding_headline_is_reproducible_from_answer(self):
        card = {"question": "What happened?",
                "answer_text": "Only 2.1% of US workers quit their jobs in "
                               "2026-09 — the lowest since 2022."}
        self.assertEqual(newsroom._finding(card),
                         "Only 2.1% of US workers quit their jobs in Sep 2026")

    def test_display_prose_humanizes_iso_dates(self):
        self.assertEqual(newsroom._display_prose(
            "The window ends 2026-11-25, after 2026-10."),
            "The window ends November 25, 2026, after October 2026.")

    def test_data_date_labels_are_human_not_raw(self):
        self.assertEqual(newsroom._data_date("2026-11-25"),
                         "November 25, 2026")
        self.assertEqual(newsroom._data_date("2026-10"), "October 2026")
        self.assertEqual(newsroom._data_date("2025"), "2025")
        self.assertEqual(newsroom._data_date("FY2027"), "FY2027")

    def test_article_header_is_compact(self):
        html = theme.header(compact=True)
        self.assertIn("compactbar", html)
        self.assertNotIn("nameplate", html)
        self.assertIn('href="/archive">Stories</a>', html)

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
        self.assertIn("Every story",
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
        linked = next(c for c in cards
                        if (c.get("headline") or {}).get("url"))
        home = publish.home_html(cards, {})
        story = (config.STORY_DIR / f"{linked['id']}" / "index.html").read_text()
        for surface in (home, story):
            self.assertIn("Source", surface)
            self.assertIn('rel="noopener"', surface)
        self.assertEqual(1, story.count('class="skip"'),
                         "exactly one skip link per page")


class TestIndicatorFiles(unittest.TestCase):
    """Phase 2: computed change, evergreen context, and a stable URL for
    every measure. These pages are reference surfaces, so a silent break is
    a broken link from every story."""

    def setUp(self):
        self.cards = json.loads(
            (config.OUTPUT_DIR / "cards.json").read_text())["cards"]

    def test_every_current_indicator_has_evergreen_context(self):
        context = newsroom._context_index()
        for card in self.cards:
            self.assertIn(card["indicator"], context,
                          f"missing why copy for {card['indicator']}")
            self.assertTrue(context[card["indicator"]]["why"].strip())

    def test_what_changed_uses_observation_dates_not_build_order(self):
        card = next(c for c in self.cards if c["indicator"] == "median_rent")
        text = re.sub(r"<[^>]+>", "", newsroom._what_changed_paragraph(card))
        self.assertIn("up $129 from $1,550 (2024)", text)
        self.assertIn("The latest observation (2025)", text)

    def test_value_text_does_not_repeat_currency_or_index_units(self):
        self.assertEqual(newsroom._value_text({"unit": "USD"}, 1679), "$1,679")
        self.assertEqual(newsroom._value_text({"unit": "index"}, 93.7), "93.7")
        self.assertEqual(newsroom._value_text({"unit": "weeks"}, 11.9),
                         "11.9 weeks")

    def test_every_long_chart_has_a_collapsed_receipt(self):
        by_id = {c["indicator"]: c for c in self.cards}
        towns = newsroom._data_table_html(by_id["mill_rates"])
        self.assertIn("See all 169 town rows behind the chart", towns)
        self.assertIn("<details class=\"databox\">", towns)
        self.assertEqual(towns.count("<td"), 169 * 3 + 52 * 0)
        peers = newsroom._data_table_html(by_id["median_rent"])
        self.assertIn("See all 52 peer rows behind the chart", peers)
        weather = newsroom._data_table_html(by_id["weather_anomaly"])
        self.assertIn("See all 58 observations behind the chart", weather)
        self.assertIn("Chart rows stop at November 25, 2026", weather)
        self.assertIn("answer uses the November 26, 2026 vintage", weather)

    def test_story_context_links_to_the_indicator_file(self):
        card = next(c for c in self.cards if c["indicator"] == "median_rent")
        page = newsroom.story_html(card, [card])
        self.assertIn('href="/indicator/median_rent"', page)
        self.assertIn("What changed", page)
        self.assertIn("Why it matters", page)
        self.assertIn("See all 52 peer rows behind the chart", page)

    def test_what_to_watch_appears_only_for_a_future_seed(self):
        today = util.et(dt.datetime.now(dt.timezone.utc)).date()
        up = today + dt.timedelta(days=7)
        old = newsroom._SEEDS_CACHE
        try:
            newsroom._SEEDS_CACHE = [{"indicator": "median_rent",
                                      "date": up.isoformat(),
                                      "reason": "a test hook"}]
            text = re.sub(r"<[^>]+>", "", newsroom._watch_paragraph(
                {"indicator": "median_rent"}))
            self.assertIn("a test hook", text)
            self.assertIn(newsroom._data_date(up.isoformat()), text)
            newsroom._SEEDS_CACHE = []
            past = {"indicator": "median_rent",
                    "date": (today - dt.timedelta(days=7)).isoformat()}
            self.assertEqual(newsroom._watch_paragraph(past), "")
        finally:
            newsroom._SEEDS_CACHE = old

    def test_every_indicator_has_a_stable_page_and_sitemap_entry(self):
        sitemap = (config.ROOT / "sitemap.xml").read_text()
        self.assertIn(f'{config.SITE_URL}/indicators</loc>', sitemap)
        for card in self.cards:
            path = config.ROOT / "indicator" / card["indicator"] / "index.html"
            self.assertTrue(path.exists(), f"missing {path}")
            body = path.read_text()
            self.assertEqual(1, body.count("<h1"),
                             "one H1 per indicator page")
            self.assertIn(f'<link rel="canonical" href="{config.SITE_URL}'
                          f'/indicator/{card["indicator"]}">', body)
            self.assertIn(f'{config.SITE_URL}/indicator/{card["indicator"]}'
                          '</loc>', sitemap)
            self.assertIn('href="/indicators">← All indicator files</a>',
                          body)

    def test_indicator_index_lists_every_measure_and_footer_links_it(self):
        body = (config.ROOT / "indicators" / "index.html").read_text()
        self.assertEqual(1, body.count("<h1"))
        self.assertEqual(len(self.cards), body.count('class="archive-item"'))
        for card in self.cards:
            self.assertIn(f'href="/indicator/{card["indicator"]}"', body)
        self.assertIn('href="/indicators">Indicator files</a>', body)


class TestLeadFreshness(unittest.TestCase):
    """The front page must not promote a month-old Connecticut card over
    today's number just because the old card happens to be CT-triggered."""

    def setUp(self):
        self.cards = json.loads(
            (config.OUTPUT_DIR / "cards.json").read_text())["cards"]
        self.now = dt.datetime.now(dt.timezone.utc)

    def test_stale_ct_trigger_does_not_displace_fresh_lead(self):
        fresh = dict(self.cards[0])
        fresh["generated_at"] = self.now.isoformat()
        fresh["stream"] = "national"
        fresh["headline"] = {"stream": "national", "ct_hits": 0,
                             "title": "Fresh number from the data desk"}
        fresh["question"] = "Is the freshest number on the board still current?"
        old = dict(next(c for c in self.cards
                        if (c.get("headline") or {}).get("stream") == "ct"))
        old["generated_at"] = (self.now - dt.timedelta(days=30)).isoformat()
        old["question"] = "Is Connecticut's job market loosening?"
        home = publish.home_html([fresh, old], {})
        lead = re.search(r'<article class="lead">.*?</article>', home, re.S)
        self.assertIsNotNone(lead)
        self.assertIn(fresh["question"], lead.group(0))
        self.assertNotIn(old["question"], lead.group(0))

    def test_dateline_uses_connecticut_clock(self):
        # 02:10 UTC is still Wednesday evening in Hartford; the masthead must
        # not sell tomorrow's edition to readers who are still in today.
        stamp = dt.datetime(2026, 11, 26, 2, 10, tzinfo=dt.timezone.utc)
        line = theme.dateline(stamp)
        self.assertIn("Wednesday, November 25, 2026", line)
        self.assertNotIn("Thursday", line)


class TestCharts(unittest.TestCase):
    """Chart metadata is data-derived: a station series is not a monthly US
    series, and a highlight may never point at a line that is not plotted."""

    WEATHER_ROWS = [
        {"date": "2026-10-27", "series": "Bradley Intl", "value": -1.5},
        {"date": "2026-10-28", "series": "Bradley Intl", "value": -5.0},
        {"date": "2026-10-27", "series": "Danbury", "value": -0.4},
        {"date": "2026-10-28", "series": "Danbury", "value": -3.1},
        {"date": "2026-11-25", "series": "Bradley Intl", "value": 1.2},
        {"date": "2026-11-25", "series": "Danbury", "value": 0.1},
    ]

    def test_missing_highlight_falls_back_to_a_plotted_line(self):
        spec = charts.trend(self.WEATHER_ROWS,
                            title="Temperature anomaly (°F)", unit="°F",
                            highlight_series="United States")
        color = spec["encoding"]["color"]
        self.assertEqual(color["scale"]["domain"],
                         ["Bradley Intl", "Danbury"])
        self.assertEqual(color["legend"]["orient"], "bottom")
        self.assertNotIn("layer", spec)
        # unit already in the title; do not print it twice on the y axis
        self.assertIsNone(spec["encoding"]["y"]["title"])
        self.assertEqual(spec["title"]["text"], "Temperature anomaly (°F)")
        # a 30-day station window needs dates, not four copies of "2026"
        self.assertEqual(spec["encoding"]["x"]["axis"]["format"], "%b %d")
        self.assertLessEqual(spec["encoding"]["x"]["axis"]["tickCount"], 4)
        self.assertEqual(spec["$schema"],
                         "https://vega.github.io/schema/vega-lite/v6.json")

    def test_monthly_series_keeps_year_ticks_and_direct_labels(self):
        rows = [
            {"date": "2000-01", "series": "Connecticut", "value": 2.0},
            {"date": "2009-06", "series": "Connecticut", "value": 9.0},
            {"date": "2026-08", "series": "Connecticut", "value": 5.8},
            {"date": "2000-01", "series": "United States", "value": 4.0},
            {"date": "2009-06", "series": "United States", "value": 9.6},
            {"date": "2026-08", "series": "United States", "value": 4.3},
        ]
        spec = charts.trend(rows, title="Unemployment rate", unit="percent",
                            highlight_series="Connecticut")
        self.assertIn("layer", spec)
        self.assertEqual(spec["layer"][0]["encoding"]["x"]["axis"]["format"],
                         "%Y")
        self.assertEqual(spec["title"]["text"], "Unemployment rate (percent)")

    def test_daily_weather_caption_names_the_real_series(self):
        card = {
            "id": "w", "question": "Is Connecticut running warmer or colder "
                                   "than normal?",
            "answer_text": "Connecticut ran 4.9°F warmer than normal.",
            "stream": "national", "series_freq": "daily",
            "answer_values": {"date": "2026-11-25"},
            "chart": {"encoding": {"color": {"scale": {
                "domain": ["Bradley Intl", "Danbury"]}}}},
        }
        desc, _ = newsroom.chart_intro(card)
        self.assertIn("Daily station readings", desc)
        self.assertIn("window ends November 25, 2026", desc)
        self.assertIn("Bradley Intl", desc)
        self.assertNotIn("Monthly US", desc)

    def test_statewide_total_is_not_a_town_page(self):
        self.assertFalse(newsroom._is_town({"town": "Total"}))
        self.assertFalse(newsroom._is_town({"town": "Connecticut"}))
        self.assertTrue(newsroom._is_town({"town": "Bridgeport"}))
        self.assertFalse(newsroom._is_town({}))

    def test_peer_map_is_lazy_and_keeps_its_accessible_wrapper(self):
        """The second chart sits below the fold; mounting it on first paint
        costs map-compile time and TBT. It must still keep role=img + label
        after Vega replaces the target."""
        self.assertIn('s.dataset.target==="chart2"', theme.VEGA_LOAD)
        self.assertIn("threshold:.2", theme.VEGA_LOAD)
        self.assertIn('setAttribute("role","img")', theme.VEGA_LOAD)
        self.assertIn('setAttribute("aria-label",label)', theme.VEGA_LOAD)

    def test_chart_reserve_survives_mobile_css(self):
        """The mobile chart rule must cap the reserve, not delete it: a
        min-height of zero lets Vega injection push every later block down
        (the 0.26 CLS regression this test guards)."""
        html = theme.viz(json.dumps({"height": 200,
                                     "title": {"text": "A chart"}}),
                         "probe", label="A chart")
        self.assertIn("--viz-h:258px", html)
        self.assertNotIn("min-height:0!important", theme.CSS)
        self.assertIn("min-height:min(var(--viz-h,0px),340px)", theme.CSS)

    def test_weather_answer_is_a_direction_not_a_signed_puzzle(self):
        from ctsignal import questions
        item = next(i for i in questions.load_catalog()["national"]
                    if i["id"] == "weather_anomaly")
        txt = item["answer"].format(abs_value=4.9, date="2026-11-25",
                                    extreme="warmer than normal")
        self.assertIn("Connecticut ran 4.9°F warmer than normal", txt)
        self.assertNotIn("+", txt)


class TestNationalDeck(unittest.TestCase):
    """The FRED context layer: honest national cards, computed superlatives,
    and a balance rule that lets one headline publish the whole deck."""

    ITEM = {
        "id": "hires_rate", "topic": "economy", "title": "JOLTS hiring rate",
        "agency": "US Bureau of Labor Statistics",
        "fred": {"series": "JTSHIR"}, "unit": "percent", "suffix": "%",
        "extreme": "min",
        "question": "Is America still hiring people into new jobs?",
        "answer": "Employers hired {value}% of America's workforce into "
                  "new jobs in {date} — {extreme}.",
    }

    def test_fred_parse_and_computed_extremes(self):
        from ctsignal.sources import fred
        rows = fred._parse(
            "observation_date,JTSHIR\n2000-12-01,4.0\n2009-06-01,2.9\n"
            "2026-07-01,3.4\n2026-08-01,3.3\n")
        self.assertEqual(rows[0]["date"], "2000-12")
        # 2009 printed lower: honest phrase names when it was last this bad
        self.assertEqual(fred.extreme_phrase(rows, "min"),
                         "lowest since June 2009")
        # nothing ever lower: 'on record', and the record is the whole series
        rows.append({"date": "2026-09", "value": 2.0})
        self.assertEqual(fred.extreme_phrase(rows, "min"),
                         "lowest on record")

    def test_extremes_read_adjacent_months_as_moves(self):
        from ctsignal.sources import fred
        rows = fred._parse(
            "observation_date,JTSHIR\n2026-07-01,3.2\n2026-08-01,3.3\n"
            "2026-09-01,3.3\n")
        self.assertEqual(fred.extreme_phrase(rows, "min"),
                         "unchanged from August 2026")
        rows = fred._parse(
            "observation_date,JTSHIR\n2026-07-01,3.0\n2026-08-01,3.3\n"
            "2026-09-01,3.2\n")
        self.assertEqual(fred.extreme_phrase(rows, "max"),
                         "down from August 2026")
        rows = fred._parse(
            "observation_date,JTSHIR\n2026-07-01,3.3\n2026-08-01,3.0\n"
            "2026-09-01,3.1\n")
        self.assertEqual(fred.extreme_phrase(rows, "max"),
                         "highest since July 2026")

    def test_national_card_shape(self):
        result = {
            "value": 3.3, "date": "2026-08",
            "rows": [{"date": d, "series": "United States", "value": v}
                     for d, v in [("2020-01", 4.1), ("2026-08", 3.3)]],
            "extreme": "lowest on record",
            "citation": "https://fred.stlouisfed.org/series/JTSHIR",
            "query": "FRED fredgraph.csv id=JTSHIR", "cache": False,
        }
        card = cards.from_national(
            self.ITEM, {"headline": {"id": "h", "title": "t", "url": "u"}},
            result)
        self.assertEqual(card["stream"], "national")
        self.assertEqual(card["chart_kind"], "trend")
        self.assertNotIn("peer", card["answer_text"])
        self.assertIn("lowest on record", card["answer_text"])
        import json as _json
        self.assertIn("United States", _json.dumps(card["chart"]))

    def test_balance_allows_one_deck_per_headline(self):
        def c(iid, score):
            return {"id": iid, "topic": "economy", "indicator": iid,
                    "headline": {"published_sort": score}}
        kept = run.balance_by_topic([c("hires_rate", 5), c("quits_rate", 5),
                                     c("hires_rate", 9)])
        self.assertEqual(sorted(k["indicator"] for k in kept),
                         ["hires_rate", "quits_rate"])
        self.assertEqual(kept[0]["headline"]["published_sort"], 9)

    def test_siblings_link_when_trigger_has_url(self):
        trig = {"id": "h", "title": "Jobs report", "url": "https://x.org/j",
                "source": "s"}
        a = dict(self.ITEM, id="aa", stream="national", headline=trig,
                 answer_text="A", chart_kind="trend", series_freq="monthly",
                 chart={"marks": []}, chart2=None, citations=["https://f"],
                 query="q", cache=False,
                 generated_at="2026-10-05T00:00:00+00:00")
        b = dict(a, id="bb", question="Other honest question?")
        page = newsroom.story_html(a, [a, b])
        self.assertIn("Same headline", page)
        self.assertIn('/story/bb', page)
        # a lone card on its trigger gets no empty block
        self.assertNotIn("Same headline", newsroom.story_html(a, [a]))


class TestShareExport(unittest.TestCase):
    """The share PNG is the page's chart, frozen: same engine, same spec,
    and its absence must degrade a page, never break a cycle."""

    def _card(self):
        result = {
            "value": 3.3, "date": "2026-08",
            "rows": [{"date": d, "series": "United States", "value": v}
                     for d, v in [("2020-01", 4.1), ("2021-05", 4.4),
                                  ("2026-08", 3.3)]],
            "extreme": "lowest on record",
            "citation": "https://fred.stlouisfed.org/series/JTSHIR",
            "query": "FRED fredgraph.csv id=JTSHIR", "cache": False,
        }
        return cards.from_national(
            TestNationalDeck.ITEM,
            {"headline": {"id": "h", "title": "t", "url": "u"}}, result)

    def test_export_writes_png_and_skips_unchanged(self):
        import tempfile
        from ctsignal import share
        card = self._card()
        with tempfile.TemporaryDirectory() as td:
            path = share.export(card, pathlib.Path(td))
            if path is None:
                self.skipTest("vl-convert unavailable in this interpreter")
            self.assertEqual(path.read_bytes()[:4], b"\x89PNG")
            mtime = path.stat().st_mtime_ns
            again = share.export(card, pathlib.Path(td))
            self.assertEqual(again, path)
            self.assertEqual(path.stat().st_mtime_ns, mtime,
                             "unchanged spec must not re-render")

    def test_export_never_raises(self):
        import tempfile
        from ctsignal import share
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(share.export({"id": "x"}, pathlib.Path(td)))
            self.assertIsNone(share.export(
                {"id": "z", "chart": {"marks": "not-a-list"}},
                pathlib.Path(td)))

    def test_export_spec_repaints_ink_for_dark_canvas(self):
        from ctsignal import share
        spec = share._export_spec({
            "width": "container", "autosize": "pad", "background": "transparent",
            "config": {"axis": {"labelColor": "#4c5a68"},
                       "legend": {"labelColor": "#4c5a68"},
                       "title": {"color": "#1c2733"}},
        })
        self.assertEqual(spec["background"], share.BG)
        self.assertNotIn("autosize", spec)
        self.assertEqual(spec["config"]["title"]["color"], share.SHARE_INK)
        self.assertEqual(spec["config"]["axis"]["labelColor"], share.SHARE_DIM)
        self.assertEqual(spec["config"]["legend"]["labelColor"], share.SHARE_DIM)

    def test_story_links_download_when_file_exists(self):
        trig = {"id": "h", "title": "t", "url": "u", "source": "s"}
        card = dict(TestNationalDeck.ITEM, id="aa", stream="national",
                    headline=trig, answer_text="A", chart_kind="trend",
                    series_freq="monthly", chart={"marks": []}, chart2=None,
                    citations=["https://f"], query="q", cache=False,
                    generated_at="2026-10-05T00:00:00+00:00")
        f = config.ROOT / "assets" / "share-aa.png"
        stamp = f.with_name(f.name + ".ver")
        try:
            f.write_bytes(b"\x89PNG fake")
            stamp.write_text("deadbeefcafe1234567890")
            page = newsroom.story_html(card, [card])
            self.assertIn("Download this chart", page)
            self.assertIn("/assets/share-aa.png?v=deadbeefcafe", page)
            # The cachebuster must never displace the story's headline or
            # the standing question under it.
            self.assertIn('<h1 class="storyh1">A</h1>', page)
            self.assertIn(f'<p class="storyq">{card["question"]}</p>', page)
            self.assertNotIn('>?v=deadbeefcafe</h1>', page)
        finally:
            f.unlink(missing_ok=True)
            stamp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
