# agent-chain

A blockchain-structured multi-agent orchestration framework in pure Python. Each agent's execution result is encapsulated as a cryptographically linked block, forming an append-only hash chain that provides tamper-evident auditability over the full execution history.

The system combines three distinct mechanisms:

- **Pipeline chaining**: sequential execution of heterogeneous agents where each agent's output feeds the next agent's input
- **Consensus validation**: a quorum-based voting protocol where designated validator agents approve or reject proposed results before they are committed
- **Immutable ledger**: a SHA-256 hash-linked block chain recording every agent action, supporting full-chain integrity verification and JSON serialization

## Architecture

```
                    Agent Pipeline
  +---------------------------------------------------+
  |  Agent_A ----block----> Agent_B ----block----> Agent_C  |
  +---------------------------|-------------------------+
                              | propose
                  +-----------v-----------+
                  |   Consensus Engine    |
                  | Validator_1 .. N vote |
                  | threshold: >= 50%     |
                  +-----------+-----------+
                              | commit (if quorum met)
                  +-----------v-----------+
                  |   Immutable Ledger    |
                  | [B0]->[B1]->[B2]->[B3] |
                  | SHA-256 hash chain    |
                  +-----------------------+
```

## Module Reference

### `block.py` -- Block and BlockHeader

`BlockHeader` is a frozen dataclass containing:

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Zero-based position in the chain |
| `timestamp` | `str` | ISO 8601 UTC timestamp |
| `prev_hash` | `str` | SHA-256 hex digest of the preceding block |
| `agent_id` | `str` | Identifier of the agent that produced this block |
| `nonce` | `int` | Reserved for future proof-of-work or ordering schemes |

`Block` wraps a `BlockHeader` and an arbitrary `payload: dict[str, Any]`. The `block_hash` is computed automatically on construction by applying SHA-256 to the deterministic JSON serialization (sorted keys, no whitespace) of the combined header and payload. Both `BlockHeader` and `Block` are frozen (immutable after creation).

`Block.from_dict()` performs hash verification on deserialization: if the recomputed hash does not match the stored `block_hash`, a `ValueError` is raised.

`Block.genesis()` produces the initial block with `prev_hash` set to `"0" * 64` and `agent_id` set to `"genesis"`.

### `ledger.py` -- ImmutableLedger

An append-only container for `Block` objects. Initialized with a genesis block at index 0.

- `append(block)` -- validates that the block's `index` equals the current chain height and that its `prev_hash` matches the latest block's hash before appending. Raises `ChainIntegrityError` on mismatch.
- `validate_chain()` -- iterates the full chain verifying index continuity, `prev_hash` linkage, and hash recomputation for every block. Returns `True` or raises `ChainIntegrityError`.
- `export_json()` / `from_json()` -- full-chain serialization to/from JSON. `from_json` runs `validate_chain()` after reconstruction.

### `agent.py` -- BaseAgent, LLMAgent, AgentResult

`BaseAgent` is an abstract class requiring subclasses to implement `execute(input_data: str, context: dict | None) -> AgentResult`. Each agent has a unique `agent_id` (auto-generated from role + UUID4 if not provided) and a `role` string.

`LLMAgent` wraps any `LLMBackend` instance. When context is provided, it is prepended to the prompt as a key-value summary. The resulting `AgentResult` includes the raw output text, backend metadata, and an ISO 8601 timestamp.

### `pipeline.py` -- AgentPipeline

Accepts an ordered list of `BaseAgent` instances and an optional `ImmutableLedger`. Calling `run(initial_input, context)` executes each agent sequentially:

1. Agent_i receives the output of Agent_{i-1} (or `initial_input` for i=0)
2. The result is wrapped as a `Block` with truncated input/output (500 chars) in the payload
3. The block is appended to the ledger
4. Context is updated with `prev_agent` and `prev_output` for downstream agents

`summary()` returns a list of dicts with step index, agent ID, role, output preview, and block hash.

### `consensus.py` -- ConsensusEngine

Accepts a list of validator agents and a configurable `threshold` (float in `(0, 1.0]`, default `0.5`).

`propose_and_vote(proposal_agent_id, payload)` sends a structured validation prompt to every validator. Each validator's response is parsed into one of three `VoteDecision` values:

| Decision | Condition |
|----------|-----------|
| `APPROVE` | Response starts with "APPROVE" (case-insensitive) |
| `REJECT` | Response starts with "REJECT" |
| `ABSTAIN` | Response starts with "ABSTAIN" or is unparseable |

If `approve_count / total_votes >= threshold`, the payload is committed as a new block in the ledger. The `ConsensusRound` dataclass tracks votes, commitment status, and the resulting block hash.

### `llm/` -- LLM Backend Adapters

All backends implement the `LLMBackend` abstract class with two methods: `name -> str` (property) and `generate(prompt, system_prompt) -> str`.

| Class | Provider | API Endpoint | Auth |
|-------|----------|-------------|------|
| `OpenAIBackend` | OpenAI Chat Completions | `POST /v1/chat/completions` | `OPENAI_API_KEY` env var or constructor arg |
| `AnthropicBackend` | Anthropic Messages | `POST /v1/messages` | `ANTHROPIC_API_KEY` env var or constructor arg |
| `OllamaBackend` | Ollama (local) | `POST /api/generate` | None (default `http://localhost:11434`) |
| `MockLLMBackend` | Deterministic mock | N/A | None |

All HTTP backends use `httpx` with configurable `timeout`, `temperature`, and `max_tokens`. `base_url` is configurable for proxy or self-hosted deployments.

`MockLLMBackend` accepts an optional `responses: dict[str, str]` mapping keywords to canned responses (case-insensitive substring match on prompt), plus a `default` fallback string. It also records all calls in `call_log` for test assertions.

## Project Structure

```
agent-chain/
    pyproject.toml
    src/
        agent_chain/
            __init__.py
            block.py
            ledger.py
            agent.py
            pipeline.py
            consensus.py
            utils.py
            llm/
                __init__.py
                base.py
                openai.py
                anthropic.py
                ollama.py
    examples/
        demo_pipeline.py
    tests/
        test_block.py
        test_ledger.py
        test_pipeline.py
        test_consensus.py
```

## Requirements

- Python >= 3.11
- Runtime dependency: `httpx >= 0.27`
- Dev dependencies: `pytest >= 8.0`, `pytest-asyncio >= 0.23`

## Installation

```bash
git clone https://github.com/jbaelaw/agent-chain.git
cd agent-chain
pip install -e ".[dev]"
```

## Usage

### Pipeline with Mock Backend

```python
from agent_chain import AgentPipeline, ImmutableLedger, LLMAgent
from agent_chain.llm import MockLLMBackend

ledger = ImmutableLedger()

researcher = LLMAgent(
    backend=MockLLMBackend(default="Quantum threats are real."),
    role="researcher",
)
analyst = LLMAgent(
    backend=MockLLMBackend(default="Migrate to PQC algorithms."),
    role="analyst",
)

pipeline = AgentPipeline([researcher, analyst], ledger=ledger)
result = pipeline.run("Assess quantum computing threats")

assert result.output == "Migrate to PQC algorithms."
assert ledger.height == 3   # genesis + 2 pipeline blocks
assert ledger.validate_chain() is True
```

### Consensus Validation

```python
from agent_chain import ConsensusEngine, LLMAgent
from agent_chain.llm import MockLLMBackend

validators = [
    LLMAgent(backend=MockLLMBackend(default="APPROVE - looks correct"), role="validator")
    for _ in range(3)
]

engine = ConsensusEngine(validators, ledger=ledger, threshold=0.67)
round_ = engine.propose_and_vote(
    proposal_agent_id=analyst.agent_id,
    payload={"report": result.output},
)

assert round_.committed is True
assert engine.tally(round_) == {"approve": 3, "reject": 0, "abstain": 0}
```

### Using Real LLM Backends

```python
from agent_chain.llm import OpenAIBackend, AnthropicBackend, OllamaBackend

agent_gpt = LLMAgent(backend=OpenAIBackend(model="gpt-4o"), role="analyst")
agent_claude = LLMAgent(backend=AnthropicBackend(model="claude-sonnet-4-20250514"), role="reviewer")
agent_local = LLMAgent(backend=OllamaBackend(model="llama3"), role="summarizer")
```

### Ledger Serialization

```python
json_str = ledger.export_json()
restored = ImmutableLedger.from_json(json_str)
assert restored.height == ledger.height
assert restored.validate_chain() is True
```

## Running the Demo

```bash
python examples/demo_pipeline.py
```

The demo runs a 3-agent pipeline (researcher, analyst, writer) followed by a 3-validator consensus round, using only `MockLLMBackend`. No API keys are required.

## Tests

```bash
pytest tests/ -v
```

29 tests covering block hashing, ledger integrity, pipeline execution, and consensus voting.

## License

MIT
