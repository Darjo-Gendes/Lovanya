import json

from app.logging_utils import log_judgment
from app import config
from app.json_utils import extract_json as _extract_json


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence():
    raw = "Sure, here you go:\n```json\n{\"a\": 1, \"b\": [1,2]}\n```"
    assert _extract_json(raw) == {"a": 1, "b": [1, 2]}


def test_extract_json_with_surrounding_prose():
    raw = 'Here is the result: {"a": 1} - hope that helps!'
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_unparseable_falls_back():
    result = _extract_json("not json at all")
    assert result["_parse_error"] is True


def test_log_judgment_appends_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "judgments.jsonl"
    monkeypatch.setattr(config, "LOG_PATH", str(log_path))

    log_judgment({"model": "qwen", "overall": 7})
    log_judgment({"model": "qwen", "overall": 8})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["overall"] == 7
    assert json.loads(lines[1])["overall"] == 8


def test_framework_file_loads():
    with open(config.FRAMEWORK_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "Output contract" in content


def test_segment_off_passthrough(monkeypatch):
    from app import segment as seg

    monkeypatch.setattr(config, "SEGMENT", "off")
    assert seg.segment("some/photo.jpg") == "some/photo.jpg"


def test_segment_never_raises(monkeypatch):
    from app import segment as seg

    monkeypatch.setattr(config, "SEGMENT", "dino")
    # nonexistent file: detection path must swallow the error and fall back
    monkeypatch.setattr(seg, "_get_detector", lambda: (_ for _ in ()).throw(RuntimeError))
    assert seg.segment("missing/photo.jpg") == "missing/photo.jpg"


def test_get_analyzer_rejects_unknown_model(monkeypatch):
    from app import analyze

    monkeypatch.setattr(config, "MODEL", "nonexistent")
    monkeypatch.setattr(analyze, "_analyzer", None)
    try:
        analyze.get_analyzer()
        assert False, "should have raised"
    except ValueError as e:
        assert "nonexistent" in str(e)
