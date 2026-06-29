"""T039 — track() attributes group/tags correctly, incl. across asyncio tasks."""

from __future__ import annotations

import asyncio

import costgen
from costgen import track


def _emit(model="demo-1"):
    costgen.record(provider="demo", model=model,
                   usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})


def test_context_manager_assigns_group(fake_provider):
    costgen.reset()
    with track("checkout", tier="free"):
        _emit()
    call = costgen.get_tracker().calls()[0]
    assert call.group == "checkout"
    assert call.tags.get("tier") == "free"


def test_decorator_assigns_group(fake_provider):
    costgen.reset()

    @track(group="batch")
    def handler():
        _emit()

    handler()
    assert costgen.get_tracker().calls()[0].group == "batch"


def test_calls_outside_scope_are_ungrouped(fake_provider):
    costgen.reset()
    _emit()
    assert costgen.get_tracker().calls()[0].group is None


def test_concurrent_async_tasks_keep_distinct_groups(fake_provider):
    costgen.reset()

    async def job(group):
        with track(group):
            await asyncio.sleep(0)  # force a context switch mid-scope
            _emit()

    async def main():
        await asyncio.gather(*(job(f"g{i}") for i in range(10)))

    asyncio.run(main())

    groups = {c.group for c in costgen.get_tracker().calls()}
    assert groups == {f"g{i}" for i in range(10)}
