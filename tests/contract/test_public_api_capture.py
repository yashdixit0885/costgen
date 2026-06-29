"""T019 — the public capture/measurement API surface exists and is callable."""

from __future__ import annotations

import costgen


def test_public_api_names_present():
    for name in (
        "install", "uninstall", "track", "record", "wrap",
        "estimate", "set_price", "load_prices",
        "report", "print_report", "export", "get_report",
        "get_tracker", "reset", "total", "__version__",
    ):
        assert hasattr(costgen, name), f"missing public API: {name}"


def test_version_string():
    assert isinstance(costgen.__version__, str) and costgen.__version__


def test_total_and_report_callable_when_empty():
    costgen.reset()
    assert costgen.total() == 0
    report = costgen.get_report()
    assert report.grand_total == 0
    assert report.schema_version == "1.0"


def test_install_uninstall_idempotent_no_error():
    costgen.install()
    costgen.install()  # idempotent
    costgen.uninstall()
    costgen.uninstall()  # safe to call when not installed
