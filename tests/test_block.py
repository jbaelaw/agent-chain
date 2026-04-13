"""Tests for Block and BlockHeader."""

from agent_chain.block import Block, BlockHeader, create_block


def test_genesis_block():
    genesis = Block.genesis()
    assert genesis.header.index == 0
    assert genesis.header.prev_hash == "0" * 64
    assert genesis.header.agent_id == "genesis"
    assert genesis.payload == {"type": "genesis"}
    assert len(genesis.block_hash) == 64


def test_block_hash_deterministic():
    header = BlockHeader(index=1, timestamp="2026-01-01T00:00:00+00:00", prev_hash="a" * 64, agent_id="test")
    b1 = Block(header=header, payload={"data": "hello"})
    b2 = Block(header=header, payload={"data": "hello"})
    assert b1.block_hash == b2.block_hash


def test_block_hash_changes_with_payload():
    header = BlockHeader(index=1, timestamp="2026-01-01T00:00:00+00:00", prev_hash="a" * 64, agent_id="test")
    b1 = Block(header=header, payload={"data": "hello"})
    b2 = Block(header=header, payload={"data": "world"})
    assert b1.block_hash != b2.block_hash


def test_create_block():
    genesis = Block.genesis()
    block = create_block(
        index=1,
        prev_hash=genesis.block_hash,
        agent_id="agent_1",
        payload={"result": "ok"},
    )
    assert block.header.index == 1
    assert block.header.prev_hash == genesis.block_hash
    assert block.payload["result"] == "ok"


def test_block_serialization_roundtrip():
    block = create_block(index=1, prev_hash="b" * 64, agent_id="test", payload={"x": 42})
    data = block.to_dict()
    restored = Block.from_dict(data)
    assert restored.block_hash == block.block_hash
    assert restored.header.agent_id == "test"
    assert restored.payload["x"] == 42


def test_block_from_dict_rejects_tampered_hash():
    block = create_block(index=1, prev_hash="c" * 64, agent_id="test", payload={"x": 1})
    data = block.to_dict()
    data["block_hash"] = "0" * 64
    try:
        Block.from_dict(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Hash mismatch" in str(e)
