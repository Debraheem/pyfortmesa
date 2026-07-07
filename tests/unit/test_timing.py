from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pyfortmesa import mesa
from pyfortmesa.mesa_support import _timed, _timed_api


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


@_timed_api("api.call")
def _dummy_api(value: int) -> int:
    return value + 1


def test_timing_disabled_by_default() -> None:
    mesa.disable_timing()
    mesa.reset_timing()

    with _timed("disabled.scope"):
        pass
    require(_dummy_api(1) == 2, "dummy api call failed")

    require(not mesa.timing_enabled(), "timing should be disabled")
    require(mesa.timing_summary() == (), "disabled timing should not record rows")


def test_timing_collects_named_scopes() -> None:
    mesa.enable_timing(reset=True)
    try:
        with _timed("test.scope"):
            sum(range(10))
        rows = mesa.timing_summary()
    finally:
        mesa.disable_timing()

    require(len(rows) == 1, "timing should record one row")
    row = rows[0]
    require(row["name"] == "test.scope", "wrong timing row name")
    require(row["calls"] == 1, "wrong timing call count")
    require(float(row["seconds"]) >= 0.0, "timing seconds should be non-negative")
    require("test.scope" in mesa.format_timing_summary(), "formatted timing missing row")


def test_timing_collects_api_calls() -> None:
    mesa.enable_timing(reset=True)
    try:
        require(_dummy_api(3) == 4, "dummy api call failed")
        rows = mesa.timing_summary()
    finally:
        mesa.disable_timing()

    require(len(rows) == 1, "api timing should record one row")
    row = rows[0]
    require(row["name"] == "api.call", "wrong api timing row name")
    require(row["calls"] == 1, "wrong api timing call count")


def test_timing_context_restores_state() -> None:
    mesa.disable_timing()
    mesa.reset_timing()

    with mesa.timing() as timing:
        require(mesa.timing_enabled(), "timing context should enable timing")
        with _timed("context.scope"):
            sum(range(5))
        require("context.scope" in timing.format(), "context format missing row")

    require(not mesa.timing_enabled(), "timing context should restore disabled state")
    require(mesa.timing_summary()[0]["name"] == "context.scope", "context row missing")


if __name__ == "__main__":
    test_timing_disabled_by_default()
    test_timing_collects_named_scopes()
    test_timing_collects_api_calls()
    test_timing_context_restores_state()
    print("timing: ok")
