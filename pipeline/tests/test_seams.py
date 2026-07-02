"""The three build seams + parsing utilities, tested without any model loaded."""
import json

from pipeline import config
from pipeline.app import analyze
from pipeline.app.json_utils import extract_json
from pipeline.app.logging_store import log_judgment
from pipeline.app.segment import segment_path


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence():
    raw = "Sure, here you go:\n```json\n{\"a\": 1, \"b\": [1,2]}\n```"
    assert extract_json(raw) == {"a": 1, "b": [1, 2]}


def test_extract_json_with_surrounding_prose():
    raw = 'Here is the result: {"a": 1} - hope that helps!'
    assert extract_json(raw) == {"a": 1}


def test_extract_json_unparseable_falls_back():
    result = extract_json("not json at all")
    assert result["_parse_error"] is True


def test_log_judgment_appends_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path))

    log_judgment("analyze", "qwen", {"occasion": "casual"}, {"overall": 7})
    log_judgment("analyze", "qwen", {"occasion": "work"}, {"overall": 8})

    lines = (tmp_path / "judgments.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["kind"] == "analyze"
    assert first["model"] == "qwen"
    assert first["output"]["overall"] == 7
    assert json.loads(lines[1])["output"]["overall"] == 8


def test_framework_file_loads():
    with open(config.FRAMEWORK_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "Output contract" in content


def test_segment_stub_passthrough():
    assert segment_path("some/photo.jpg") == "some/photo.jpg"


def test_get_analyzer_rejects_unknown_model(monkeypatch):
    monkeypatch.setattr(config, "MODEL", "nonexistent")
    monkeypatch.setattr(analyze, "_analyzer", None)
    try:
        analyze.get_analyzer()
        assert False, "should have raised"
    except ValueError as e:
        assert "nonexistent" in str(e)
