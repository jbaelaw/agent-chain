#!/usr/bin/env python3
"""Demo: 3-agent pipeline with consensus validation.

Runs entirely with MockLLMBackend — no API keys needed.
"""

from agent_chain.llm.base import MockLLMBackend
from agent_chain.agent import LLMAgent
from agent_chain.pipeline import AgentPipeline
from agent_chain.consensus import ConsensusEngine
from agent_chain.ledger import ImmutableLedger


def main() -> None:
    ledger = ImmutableLedger()

    # --- LLM backends (mock) ---
    researcher_llm = MockLLMBackend(default="Research findings: quantum computing can break RSA-2048 by 2030.")
    analyst_llm = MockLLMBackend(default="Analysis: migrate to post-quantum algorithms (CRYSTALS-Kyber, Dilithium).")
    writer_llm = MockLLMBackend(default="Report: organizations should begin PQC migration within 2 years.")

    # --- Pipeline agents ---
    researcher = LLMAgent(backend=researcher_llm, role="researcher", system_prompt="You research topics deeply.")
    analyst = LLMAgent(backend=analyst_llm, role="analyst", system_prompt="You analyze research findings.")
    writer = LLMAgent(backend=writer_llm, role="writer", system_prompt="You write executive summaries.")

    # --- Run pipeline ---
    print("=" * 60)
    print("PHASE 1: Agent Pipeline (Researcher -> Analyst -> Writer)")
    print("=" * 60)

    pipeline = AgentPipeline([researcher, analyst, writer], ledger=ledger)
    final_result = pipeline.run("Assess quantum computing threats to current cryptography")

    for step in pipeline.summary():
        print(f"\n  Step {step['step']} [{step['role']}]")
        print(f"  Output: {step['output_preview']}")
        print(f"  Block:  {step['block_hash'][:32]}...")

    print(f"\n  Final output: {final_result.output}")

    # --- Consensus validation ---
    print("\n" + "=" * 60)
    print("PHASE 2: Consensus Validation")
    print("=" * 60)

    validator_llms = [
        MockLLMBackend(default="APPROVE - report is accurate and well-structured"),
        MockLLMBackend(default="APPROVE - recommendations are sound"),
        MockLLMBackend(default="REJECT - needs more specific timelines"),
    ]
    validators = [
        LLMAgent(backend=llm, role="validator")
        for llm in validator_llms
    ]

    engine = ConsensusEngine(validators, ledger=ledger, threshold=0.5)
    round_ = engine.propose_and_vote(
        proposal_agent_id=writer.agent_id,
        payload={"report": final_result.output},
    )

    tally = engine.tally(round_)
    print(f"\n  Votes: {tally}")
    print(f"  Committed: {round_.committed}")
    if round_.block_hash:
        print(f"  Block:  {round_.block_hash[:32]}...")

    # --- Ledger summary ---
    print("\n" + "=" * 60)
    print("PHASE 3: Immutable Ledger")
    print("=" * 60)

    print(f"\n  Chain height: {ledger.height} blocks")
    print(f"  Chain valid:  {ledger.validate_chain()}")

    for block in ledger:
        agent = block.header.agent_id
        idx = block.header.index
        print(f"  [{idx}] agent={agent:<20s} hash={block.block_hash[:24]}...")

    print()


if __name__ == "__main__":
    main()
