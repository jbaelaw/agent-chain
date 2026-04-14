"""Tests for Merkle tree utilities."""

from agent_chain.merkle import merkle_root, chain_merkle_root
from agent_chain.ledger import ImmutableLedger
from agent_chain.block import create_block
from agent_chain.utils import sha256_hex


def test_merkle_root_empty():
    assert merkle_root([]) == "0" * 64


def test_merkle_root_single():
    h = sha256_hex("block0")
    assert merkle_root([h]) == h


def test_merkle_root_two():
    h1 = sha256_hex("a")
    h2 = sha256_hex("b")
    expected = sha256_hex(h1 + h2)
    assert merkle_root([h1, h2]) == expected


def test_merkle_root_odd_count():
    h1 = sha256_hex("a")
    h2 = sha256_hex("b")
    h3 = sha256_hex("c")
    pair_12 = sha256_hex(h1 + h2)
    pair_33 = sha256_hex(h3 + h3)
    expected = sha256_hex(pair_12 + pair_33)
    assert merkle_root([h1, h2, h3]) == expected


def test_merkle_root_four():
    hashes = [sha256_hex(str(i)) for i in range(4)]
    left = sha256_hex(hashes[0] + hashes[1])
    right = sha256_hex(hashes[2] + hashes[3])
    expected = sha256_hex(left + right)
    assert merkle_root(hashes) == expected


def test_chain_merkle_root():
    ledger = ImmutableLedger()
    for i in range(1, 4):
        block = create_block(
            index=i,
            prev_hash=ledger.latest.block_hash,
            agent_id=f"a{i}",
            payload={"i": i},
        )
        ledger.append(block)

    root = chain_merkle_root(ledger)
    assert len(root) == 64

    hashes = [b.block_hash for b in ledger]
    assert root == merkle_root(hashes)


def test_merkle_root_deterministic():
    hashes = [sha256_hex(str(i)) for i in range(8)]
    r1 = merkle_root(hashes)
    r2 = merkle_root(hashes)
    assert r1 == r2


def test_merkle_root_changes_with_input():
    h1 = [sha256_hex("a"), sha256_hex("b")]
    h2 = [sha256_hex("a"), sha256_hex("c")]
    assert merkle_root(h1) != merkle_root(h2)
