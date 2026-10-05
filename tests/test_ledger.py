"""The headline ledger: ingestion memory, heat rollup, TTL discipline."""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ctsignal import questions  # noqa: E402

CATALOG = {"national": [
    {"id": "jobless_claims", "keywords": ["jobless claim", "layoff"]},
    {"id": "hires_rate", "keywords": ["hiring", "labor market"]},
]}


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self._old = questions.LEDGER_PATH
        questions.LEDGER_PATH = pathlib.Path(self.dir.name) / "ledger.json"
        self.addCleanup(questions.__dict__.__setitem__, "LEDGER_PATH", self._old)
        self.addCleanup(self.dir.cleanup)

    def _ent(self):
        return json.loads(questions.LEDGER_PATH.read_text())["entries"]

    def test_ingest_maps_and_keeps_gaps(self):
        questions.update_ledger([
            {"id": "a1", "title": "Layoff wave hits Ohio plant", "source": "x"},
            {"id": "a2", "title": "Hiring cools, labor market softens",
             "source": "y"},
            {"id": "a3", "title": "Weather today", "source": "z"},
        ], CATALOG)
        ent = self._ent()
        self.assertEqual(ent["a1"]["hits"], ["jobless_claims"])
        self.assertEqual(sorted(ent["a2"]["hits"]), ["hires_rate"])
        self.assertEqual(ent["a3"]["hits"], [])  # kept: the gap is the roadmap
        att = questions.attention(7)
        self.assertEqual(att["headlines"], 3)
        self.assertEqual(att["indicators"]["jobless_claims"]["hits"], 1)

    def test_reingest_does_not_double_count(self):
        questions.update_ledger([{"id": "a1", "title": "Layoff report lands",
                                  "source": "x"}], CATALOG)
        questions.update_ledger([{"id": "a1", "title": "Layoff report lands",
                                  "source": "x"}], CATALOG)
        self.assertEqual(questions.attention(7)["indicators"]
                         ["jobless_claims"]["hits"], 1)

    def test_ttl_prunes_old_entries(self):
        questions.update_ledger([], CATALOG)
        data = {"entries": {"old": {
            "ts": (dt.datetime.now(dt.timezone.utc)
                   - dt.timedelta(days=questions.LEDGER_TTL_DAYS + 5)
                   ).isoformat(timespec="seconds"),
            "src": "", "title": "", "hits": ["hires_rate"]}}}
        questions.LEDGER_PATH.write_text(json.dumps(data))
        questions.update_ledger([], CATALOG)
        self.assertNotIn("old", self._ent())


if __name__ == "__main__":
    unittest.main()
