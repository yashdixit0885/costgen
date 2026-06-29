"""T047 (local portion) — package imports cleanly and exposes a version."""

from __future__ import annotations


def test_import_and_version():
    import costgen

    assert isinstance(costgen.__version__, str)
    assert costgen.__version__
