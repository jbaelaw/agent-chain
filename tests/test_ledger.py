"""Tests for ImmutableLedger."""

import pytest

from agent_chain.block import Block, create_block
from agent_chain.ledger import ImmutableLedger, ChainIntegrityError


def test_ledger_starts_with_genesis():
    ledger = ImmutableLedger()
    assert ledger.height == 1
    assert ledger.latest.header.index == 0
    assert ledger.latest.header.agent_id == "genesis"


def test_append_valid_block():
    ledger = ImmutableLedger()
    block = create_block(
        index=1,
        prev_hash=ledger.latest.block_hash,
        agent_id="a1",
        payload={"step": 1},
    )
    ledger.append(block)
    assert ledger.height == 2
    assert ledger.latest.block_hash == block.block_hash


def test_append_rejects_wrong_index():
    ledger = ImmutableLedger()
    block = create_block(index=5, prev_hash=ledger.latest.block_hash, agent_id="a1", payload={})
    with pytest.raises(ChainIntegrityError, match="Expected block index"):
        ledger.append(block)


def test_append_rejects_wrong_prev_hash():
    ledger = ImmutableLedger()
    block = create_block(index=1, prev_hash="bad" * 21 + "b", agent_id="a1", payload={})
    with pytest.raises(ChainIntegrityError, match="prev_hash"):
        ledger.append(block)


def test_validate_chain_ok():
    ledger = ImmutableLedger()
    for i in range(1, 5):
        block = create_block(
            index=i,
            prev_hash=ledger.latest.block_hash,
            agent_id=f"agent_{i}",
            payload={"i": i},
        )
        ledger.append(block)
    assert ledger.validate_chain() is True


def test_iteration():
    ledger = ImmutableLedger()
    block = create_block(index=1, prev_hash=ledger.latest.block_hash, agent_id="a", payload={})
    ledger.append(block)
    blocks = list(ledger)
    assert len(blocks) == 2


def test_export_import_roundtrip():
    ledger = ImmutableLedger()
    for i in range(1, 4):
        block = create_block(
            index=i,
            prev_hash=ledger.latest.block_hash,
            agent_id=f"a{i}",
            payload={"val": i},
        )
        ledger.append(block)

    json_str = ledger.export_json()
    restored = ImmutableLedger.from_json(json_str)
    assert restored.height == ledger.height
    assert restored.latest.block_hash == ledger.latest.block_hash


def test_get_block():
    ledger = ImmutableLedger()
    block = create_block(index=1, prev_hash=ledger.latest.block_hash, agent_id="x", payload={})
    ledger.append(block)
    assert ledger.get_block(0).header.agent_id == "genesis"
    assert ledger.get_block(1).header.agent_id == "x"
    with pytest.raises(IndexError):
        ledger.get_block(99)
