"""Block and BlockHeader — the fundamental unit of the agent chain."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any

from .utils import sha256_hex, deterministic_json, utc_now, new_id


@dataclass(frozen=True)
class BlockHeader:
    index: int
    timestamp: str
    prev_hash: str
    agent_id: str
    nonce: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Block:
    header: BlockHeader
    payload: dict[str, Any]
    block_hash: str = field(init=False)

    def __post_init__(self) -> None:
        computed = self._compute_hash()
        object.__setattr__(self, "block_hash", computed)

    def _compute_hash(self) -> str:
        raw = deterministic_json({
            "header": self.header.to_dict(),
            "payload": self.payload,
        })
        return sha256_hex(raw)

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "payload": self.payload,
            "block_hash": self.block_hash,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Block:
        header = BlockHeader(**data["header"])
        block = cls(header=header, payload=data["payload"])
        if block.block_hash != data.get("block_hash"):
            raise ValueError(
                f"Hash mismatch: computed {block.block_hash}, "
                f"expected {data.get('block_hash')}"
            )
        return block

    @staticmethod
    def genesis() -> Block:
        header = BlockHeader(
            index=0,
            timestamp=utc_now(),
            prev_hash="0" * 64,
            agent_id="genesis",
            nonce=0,
        )
        return Block(header=header, payload={"type": "genesis"})


def create_block(
    *,
    index: int,
    prev_hash: str,
    agent_id: str,
    payload: dict[str, Any],
    nonce: int = 0,
) -> Block:
    header = BlockHeader(
        index=index,
        timestamp=utc_now(),
        prev_hash=prev_hash,
        agent_id=agent_id,
        nonce=nonce,
    )
    return Block(header=header, payload=payload)
