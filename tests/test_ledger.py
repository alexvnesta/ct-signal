class DummyDate:
    pass


def test_ledger_and_attention(tmp_path, monkeypatch):
    import datetime as dt
    import json
    from ctsignal import questions

    monkeypatch.setattr(questions, "LEDGER_PATH", tmp_path / "ledger.json")
    catalog = {"national": [
        {"id": "jobless_claims", "keywords": ["jobless claim", "layoff"]},
        {"id": "hires_rate", "keywords": ["hiring", "labor market"]},
    ]}
    hl = [{"id": "a1", "title": "Layoff wave hits Ohio plant", "source": "x"},
          {"id": "a2", "title": "Hiring cools, labor market softens",
           "source": "y"},
          {"id": "a3", "title": "Weather today", "source": "z"}]
    questions.update_ledger(hl, catalog)
    ent = json.loads((tmp_path / "ledger.json").read_text())["entries"]
    assert ent["a1"]["hits"] == ["jobless_claims"]
    assert sorted(ent["a2"]["hits"]) == ["hires_rate"]
    assert ent["a3"]["hits"] == []          # kept, unmapped: that's the gap
    att = questions.attention(7)
    assert att["headlines"] == 3
    assert att["indicators"]["jobless_claims"]["hits"] == 1

    # Re-ingest must not double-count, and TTL pruning must bite.
    questions.update_ledger(hl + [{"id": "a4", "title": "More layoffs",
                                   "source": "w"}], catalog)
    att = questions.attention(7)
    assert att["indicators"]["jobless_claims"]["hits"] == 2
    data = json.loads((tmp_path / "ledger.json").read_text())
    data["entries"]["old"] = {
        "ts": (dt.datetime.now(dt.timezone.utc)
               - dt.timedelta(days=questions.LEDGER_TTL_DAYS + 5)
               ).isoformat(timespec="seconds"), "src": "", "title": "",
        "hits": ["hires_rate"]}
    (tmp_path / "ledger.json").write_text(json.dumps(data))
    questions.update_ledger([], catalog)
    assert "old" not in json.loads(
        (tmp_path / "ledger.json").read_text())["entries"]
