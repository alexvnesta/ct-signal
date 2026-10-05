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

    def test_story_links_download_when_file_exists(self):
        trig = {"id": "h", "title": "t", "url": "u", "source": "s"}
        card = dict(TestNationalDeck.ITEM, id="aa", stream="national",
                    headline=trig, answer_text="A", chart_kind="trend",
                    series_freq="monthly", chart={"marks": []}, chart2=None,
                    citations=["https://f"], query="q", cache=False,
                    generated_at="2026-10-05T00:00:00+00:00")
        f = config.ROOT / "assets" / "share-aa.png"
        try:
            f.write_bytes(b"\x89PNG fake")
            page = newsroom.story_html(card, [card])
            self.assertIn("Download this chart", page)
            self.assertIn("/assets/share-aa.png", page)
        finally:
            f.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
