"""House style guards for generated prose (see docs/STYLE.md).

The templates in catalog/indicators.yaml are the entire voice surface of a
card answer, so they are cheap to police in CI: banned phrases, the old
definition footnote, double periods, and stacked em-dashes are all regex
away from never coming back."""
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

BANNED = [
    "it's not just", "not merely", "delve", "moreover", "furthermore",
    "worth noting", "when it comes to", "in today's", "seamless", "robust",
    "crucial", "vital", "foster", "leverag", "harness", "unlock",
    "revolutioniz", "testament", "underscor", "stands as", "serves as",
    "landscape", "tapestry", "embark", "game-chang",
]


class TestAnswerTemplates(unittest.TestCase):
    def setUp(self):
        cat = yaml.safe_load((ROOT / "catalog" / "indicators.yaml").read_text())
        items = list(cat.get("stackup", [])) + list(cat.get("local", []))
        # items answered in code (answerer: town_metric_growth) build their
        # sentences in the answerer; only template items are policed here
        self.items = [i for i in items if "answer" in i]
        self.assertGreaterEqual(len(self.items), 4, "nothing policed")

    def test_no_definition_footnote(self):
        for item in self.items:
            self.assertNotIn(
                "(50 states", item["answer"],
                f"{item['id']}: peer-set definition belongs in the page "
                "legend, not every answer")

    def test_no_banned_phrases(self):
        for item in self.items:
            low = item["answer"].lower()
            for phrase in BANNED:
                self.assertNotIn(phrase, low, f"{item['id']}: {phrase!r}")

    def test_single_terminal_period(self):
        for item in self.items:
            self.assertTrue(item["answer"].endswith("."), item["id"])
            self.assertFalse(item["answer"].endswith(".."), item["id"])
            self.assertNotIn("..", item["answer"][:-1], item["id"])

    def test_no_em_dash_tails(self):
        # the old six identical " — the Nth-highest…" tails; commas do this
        for item in self.items:
            self.assertNotIn(" \u2014 ", item["answer"], item["id"])

    def test_templates_format_clean(self):
        # every {placeholder} must be satisfiable by the documented field set
        fields = {"value", "date", "rank", "n", "rank_word", "low_word",
                  "top_town", "added", "pct", "latest_year",
                  # mill-rate grammar (from_mill_rates)
                  "rate", "multiple", "state", "fiscal_year"}
        for item in self.items:
            used = set(re.findall(r"\{(\w+)\}", item["answer"]))
            self.assertTrue(used <= fields, f"{item['id']}: {used - fields}")


if __name__ == "__main__":
    unittest.main()
