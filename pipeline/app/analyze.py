from . import config
from .logging_utils import log_judgment
from .segment import segment

_analyzer = None


def get_analyzer():
    """Swappable model boundary: config.MODEL picks the analyzer.

    Adding another model is a one-line change: add an elif branch here.
    """
    global _analyzer
    if _analyzer is not None:
        return _analyzer
    if config.MODEL == "qwen":
        from .qwen_analyzer import QwenAnalyzer

        _analyzer = QwenAnalyzer()
    else:
        raise ValueError(f"Unknown MODEL: {config.MODEL!r}")
    return _analyzer


def analyze(image_path: str, occasion: str) -> dict:
    analyzer = get_analyzer()
    region_path = segment(image_path)
    perception = analyzer.perceive(region_path)
    judgment = analyzer.judge(region_path, perception, occasion)
    record = {
        "model": config.MODEL,
        "image_path": image_path,
        "occasion": occasion,
        "perception": perception,
        "judgment": judgment,
    }
    log_judgment(record)
    return record
