"""T: model-id alias resolution for dated snapshots and cloud-prefixed ids."""

from __future__ import annotations

from decimal import Decimal

from costgen._pricing._alias import candidates
from costgen._pricing.loader import load_bundled


def test_dated_snapshot_candidates():
    assert "gpt-4o" in candidates("gpt-4o-2024-08-06")
    assert "gpt-4o-mini" in candidates("gpt-4o-mini-2024-07-18")


def test_bedrock_prefix_candidates():
    cands = candidates("us.anthropic.claude-opus-4-8")
    assert "claude-opus-4-8" in cands
    cands2 = candidates("anthropic.claude-opus-4-8")
    assert "claude-opus-4-8" in cands2


def test_vertex_version_candidates():
    assert "claude-opus-4-8" in candidates("claude-opus-4-8@20251101")


def test_original_is_first_candidate():
    assert candidates("gpt-4o-2024-08-06")[0] == "gpt-4o-2024-08-06"


def test_no_match_for_unknown_base():
    # Old model we don't bundle -> base still derived but won't price.
    assert "claude-3-5-sonnet" in candidates("claude-3-5-sonnet-20241022")


def test_lookup_resolves_dated_openai_snapshot():
    reg = load_bundled()
    rec = reg.lookup("openai", "gpt-4o-2024-08-06")
    assert rec is not None and rec.model == "gpt-4o"
    assert rec.input_price_per_mtok == Decimal("2.50")


def test_lookup_resolves_bedrock_prefixed_anthropic():
    reg = load_bundled()
    rec = reg.lookup("anthropic", "us.anthropic.claude-opus-4-8")
    assert rec is not None and rec.model == "claude-opus-4-8"
    assert rec.input_price_per_mtok == Decimal("5.00")


def test_exact_override_wins_over_alias():
    reg = load_bundled()
    reg.set_override(
        provider="openai", model="gpt-4o-2024-08-06",
        input_price_per_mtok="9.99", output_price_per_mtok="19.99",
        source="azure-contract", last_verified="2026-06-29",
    )
    rec = reg.lookup("openai", "gpt-4o-2024-08-06")
    assert rec.source == "azure-contract"
    assert rec.input_price_per_mtok == Decimal("9.99")


def test_resolve_aliases_can_be_disabled():
    reg = load_bundled()
    assert reg.lookup("openai", "gpt-4o-2024-08-06", resolve_aliases=False) is None
