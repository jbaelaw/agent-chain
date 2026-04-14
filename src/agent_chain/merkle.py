"""Merkle tree utilities for chain summary hashing."""

from __future__ import annotations

from .utils import sha256_hex


def merkle_root(hashes: list[str]) -> str:
    """Compute the Merkle root of a list of hex hash strings.

    If the list has odd length, the last element is duplicated before pairing.
    Returns the all-zeros hash for an empty list.
    """
    if not hashes:
        return "0" * 64

    level = list(hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level: list[str] = []
        for i in range(0, len(level), 2):
            combined = level[i] + level[i + 1]
            next_level.append(sha256_hex(combined))
        level = next_level

    return level[0]


def chain_merkle_root(ledger) -> str:
    """Compute the Merkle root over all block hashes in a ledger."""
    hashes = [block.block_hash for block in ledger]
    return merkle_root(hashes)
