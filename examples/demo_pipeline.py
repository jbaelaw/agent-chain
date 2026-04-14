#!/usr/bin/env python3
"""Demo: full agent-chain workflow with pipeline, consensus, branching, events, and Merkle root.

Runs entirely with MockLLMBackend -- no API keys needed.
"""

from agent_chain.llm.base import MockLLMBackend
from agent_chain.agent import LLMAgent
from agent_chain.function_agent import FunctionAgent
from agent_chain.pipeline import AgentPipeline
from agent_chain.consensus import ConsensusEngine
from agent_chain.branch_pipeline import BranchPipeline
from agent_chain.merkle import chain_merkle_root
from agent_chain.events import EventBus, EventType
from agent_chain.ledger import ImmutableLedger


def main() -> None:
    ledger = ImmutableLedger()

    event_log: list[str] = []
    bus = EventBus()
    bus.on_all(lambda et, d: event_log.append(et.value))

    # -- Phase 1: Pipeline with mixed agent types --
    print("=" * 60)
    print("PHASE 1: Mixed Pipeline (LLM + Function agents)")
    print("=" * 60)

    researcher = LLMAgent(
        backend=MockLLMBackend(default="Quantum threats: RSA-2048 breakable by 2030."),
        role="researcher",
    )
    normalizer = FunctionAgent(
        lambda text, ctx: text.strip().upper(),
        role="normalizer",
    )
    analyst = LLMAgent(
        backend=MockLLMBackend(default="Recommendation: migrate to CRYSTALS-Kyber and Dilithium."),
        role="analyst",
    )

    pipeline = AgentPipeline([researcher, normalizer, analyst], ledger=ledger, event_bus=bus)
    final_result = pipeline.run("Assess quantum computing threats to current cryptography")

    for step in pipeline.summary():
        print(f"\n  Step {step['step']} [{step['role']}]")
        print(f"  Output: {step['output_preview']}")
        print(f"  Block:  {step['block_hash'][:32]}...")
    print(f"\n  Final: {final_result.output}")

    # -- Phase 2: Conditional Branching --
    print("\n" + "=" * 60)
    print("PHASE 2: Conditional Branching")
    print("=" * 60)

    def router(text, ctx):
        return "detailed" if len(text) > 50 else "brief"

    branch = BranchPipeline(
        router=router,
        branches={
            "brief": [
                FunctionAgent(lambda t, c: f"Brief: {t[:60]}", role="brief_writer"),
            ],
            "detailed": [
                LLMAgent(
                    backend=MockLLMBackend(default="Detailed report: PQC migration roadmap with timelines."),
                    role="report_writer",
                ),
            ],
        },
        ledger=ledger,
    )
    branch_result = branch.run(final_result.output)
    print(f"\n  Router chose: {branch.results[0].branch_name}")
    print(f"  Output: {branch_result.output}")

    # -- Phase 3: Consensus --
    print("\n" + "=" * 60)
    print("PHASE 3: Consensus Validation")
    print("=" * 60)

    validators = [
        LLMAgent(backend=MockLLMBackend(default="APPROVE - accurate"), role="validator"),
        LLMAgent(backend=MockLLMBackend(default="APPROVE - sound"), role="validator"),
        LLMAgent(backend=MockLLMBackend(default="REJECT - needs timelines"), role="validator"),
    ]
    engine = ConsensusEngine(validators, ledger=ledger, threshold=0.5, event_bus=bus)
    round_ = engine.propose_and_vote(
        proposal_agent_id=analyst.agent_id,
        payload={"report": branch_result.output},
    )

    tally = engine.tally(round_)
    print(f"\n  Votes: {tally}")
    print(f"  Committed: {round_.committed}")
    if round_.block_hash:
        print(f"  Block: {round_.block_hash[:32]}...")

    # -- Phase 4: Ledger + Merkle --
    print("\n" + "=" * 60)
    print("PHASE 4: Ledger and Merkle Root")
    print("=" * 60)

    print(f"\n  Chain height: {ledger.height} blocks")
    print(f"  Chain valid:  {ledger.validate_chain()}")
    print(f"  Merkle root:  {chain_merkle_root(ledger)[:32]}...")

    for block in ledger:
        agent = block.header.agent_id
        idx = block.header.index
        print(f"  [{idx}] agent={agent:<30s} hash={block.block_hash[:20]}...")

    # -- Phase 5: Event Log --
    print("\n" + "=" * 60)
    print("PHASE 5: Event Log")
    print("=" * 60)

    print(f"\n  Total events fired: {len(event_log)}")
    for ev in event_log:
        print(f"    {ev}")

    print()


if __name__ == "__main__":
    main()
