"""Repo-root pytest setup.

Tests run against the GPU-free honest-mock analyzer on every machine (the
qwen analyzer needs torch + the GPU box; its seams are unit-tested without
loading it). Set before any `pipeline.config` import so the default applies.
"""
import os
import sys

os.environ.setdefault("LOVANYA_MODEL", "honest-mock")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
