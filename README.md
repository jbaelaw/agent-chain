# agent-chain

Blockchain-structured AI Agent system. Agents are linked like blocks in a chain — each agent's output becomes the next agent's input, results are validated through consensus voting, and the entire history is recorded in an immutable ledger.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Agent Pipeline                      │
│  Agent_A ──block──▶ Agent_B ──block──▶ Agent_C      │
└──────────────────────┬──────────────────────────────┘
                       │ propose
          ┌────────────▼────────────┐
          │    Consensus Engine     │
          │  Validator₁  Validator₂ │
          │    vote ✓      vote ✗   │
          └────────────┬────────────┘
                       │ commit (if quorum)
          ┌────────────▼────────────┐
          │    Immutable Ledger     │
          │  [B₀]→[B₁]→[B₂]→[B₃]  │
          │   SHA-256 hash chain    │
          └─────────────────────────┘
```

### Three Core Mechanisms

1. **Pipeline Chaining** — Agents execute in sequence. Each agent's output is the next agent's input, forming a processing pipeline (e.g., Researcher → Analyst → Writer).

2. **Consensus Validation** — Validator agents review and vote (APPROVE / REJECT / ABSTAIN) on results. A configurable quorum threshold determines whether a result is committed.

3. **Immutable Ledger** — Every agent result is recorded as a block with SHA-256 hash chaining. The full chain is tamper-evident and can be exported/imported as JSON.

## Installation

```bash
pip install -e .

# With dev dependencies (pytest)
pip install -e ".[dev]"
```

## Quick Start

```python
from agent_chain import AgentPipeline, ConsensusEngine, ImmutableLedger, LLMAgent
from agent_chain.llm import MockLLMBackend

# Create a shared ledger
ledger = ImmutableLedger()

# Define agents with mock backends (swap for OpenAI/Anthropic/Ollama in production)
researcher = LLMAgent(
    backend=MockLLMBackend(default="Quantum threats are real."),
    role="researcher",
)
analyst = LLMAgent(
    backend=MockLLMBackend(default="Migrate to PQC algorithms."),
    role="analyst",
)

# Run pipeline
pipeline = AgentPipeline([researcher, analyst], ledger=ledger)
result = pipeline.run("Assess quantum computing threats")
print(result.output)  # "Migrate to PQC algorithms."

# Validate with consensus
validators = [
    LLMAgent(backend=MockLLMBackend(default="APPROVE looks good"), role="validator")
    for _ in range(3)
]
engine = ConsensusEngine(validators, ledger=ledger, threshold=0.5)
round_ = engine.propose_and_vote(
    proposal_agent_id=analyst.agent_id,
    payload={"report": result.output},
)
print(f"Committed: {round_.committed}")  # True
print(f"Chain height: {ledger.height}")  # 4 (genesis + 2 pipeline + 1 consensus)
```

## LLM Backends

| Backend | Class | Config |
|---------|-------|--------|
| OpenAI | `OpenAIBackend` | `OPENAI_API_KEY` env var |
| Anthropic | `AnthropicBackend` | `ANTHROPIC_API_KEY` env var |
| Ollama | `OllamaBackend` | `OLLAMA_HOST` env var (default: `localhost:11434`) |
| Mock | `MockLLMBackend` | No config needed |

```python
from agent_chain.llm import OpenAIBackend, AnthropicBackend, OllamaBackend

# Use any backend interchangeably
agent = LLMAgent(backend=OpenAIBackend(model="gpt-4o"), role="analyst")
agent = LLMAgent(backend=AnthropicBackend(model="claude-sonnet-4-20250514"), role="analyst")
agent = LLMAgent(backend=OllamaBackend(model="llama3"), role="analyst")
```

## Running the Demo

```bash
python examples/demo_pipeline.py
```

## Tests

```bash
pytest tests/ -v
```

## License

MIT
