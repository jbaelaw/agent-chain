"""ImmutableLedger — append-only blockchain of agent results."""

from __future__ import annotations

import json
from typing import Any, Iterator

from .block import Block


class ChainIntegrityError(Exception):
    """Raised when the chain fails a validation check."""


class ImmutableLedger:
    """Append-only chain of blocks with hash-linked integrity."""

    def __init__(self) -> None:
        self._chain: list[Block] = []
        genesis = Block.genesis()
        self._chain.append(genesis)

    @property
    def height(self) -> int:
        return len(self._chain)

    @property
    def latest(self) -> Block:
        return self._chain[-1]

    def append(self, block: Block) -> None:
        expected_index = self.height
        if block.header.index != expected_index:
            raise ChainIntegrityError(
                f"Expected block index {expected_index}, got {block.header.index}"
            )
        if block.header.prev_hash != self.latest.block_hash:
            raise ChainIntegrityError(
                f"Block prev_hash {block.header.prev_hash!r} does not match "
                f"latest hash {self.latest.block_hash!r}"
            )
        self._chain.append(block)

    def validate_chain(self) -> bool:
        for i in range(1, len(self._chain)):
            prev, curr = self._chain[i - 1], self._chain[i]
            if curr.header.prev_hash != prev.block_hash:
                raise ChainIntegrityError(
                    f"Block {i}: prev_hash mismatch "
                    f"(expected {prev.block_hash!r}, got {curr.header.prev_hash!r})"
                )
            if curr.header.index != i:
                raise ChainIntegrityError(
                    f"Block {i}: index mismatch (got {curr.header.index})"
                )
            recomputed = curr._compute_hash()
            if recomputed != curr.block_hash:
                raise ChainIntegrityError(
                    f"Block {i}: hash tampered "
                    f"(expected {recomputed!r}, stored {curr.block_hash!r})"
                )
        return True

    def get_block(self, index: int) -> Block:
        if index < 0 or index >= len(self._chain):
            raise IndexError(f"Block index {index} out of range [0, {self.height})")
        return self._chain[index]

    def __iter__(self) -> Iterator[Block]:
        return iter(self._chain)

    def __len__(self) -> int:
        return len(self._chain)

    def export_json(self, indent: int = 2) -> str:
        return json.dumps(
            [b.to_dict() for b in self._chain], indent=indent, default=str
        )

    @classmethod
    def from_json(cls, data: str) -> ImmutableLedger:
        blocks_data: list[dict[str, Any]] = json.loads(data)
        if not blocks_data:
            raise ChainIntegrityError("Cannot restore an empty chain")
        ledger = cls.__new__(cls)
        ledger._chain = []
        for bd in blocks_data:
            block = Block.from_dict(bd)
            ledger._chain.append(block)
        if ledger._chain[0].header.index != 0:
            raise ChainIntegrityError(
                f"First block must have index 0, got {ledger._chain[0].header.index}"
            )
        ledger.validate_chain()
        return ledger
