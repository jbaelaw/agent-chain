# agent-chain

A blockchain-structured multi-agent orchestration framework in pure Python. Each agent's execution result is encapsulated as a cryptographically linked block, forming an append-only hash chain that provides tamper-evident auditability over the full execution history.

The system combines five mechanisms:

- **Pipeline chaining**: sequential execution of heterogeneous agents where each agent's output feeds the next agent's input
- **Consensus validation**: a quorum-based voting protocol where designated validator agents approve or reject proposed results
- **Immutable ledger**: a SHA-256 hash-linked block chain recording every agent action, with full-chain integrity verification
- **Branching and fan-out**: conditional routing to named branches, or parallel execution of multiple branches with result aggregation
- **Event hooks**: a publish/subscribe EventBus that fires on agent start/end, block creation, consensus votes, and pipeline lifecycle

Both synchronous and asynchronous execution models are supported. Async consensus collects validator votes concurrently via `asyncio.gather`.

## Architecture

```
                    Agent Pipeline (sync or async)
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
                  | Merkle root summary   |
                  +-----------------------+
                              |
                  +-----------v-----------+
                  |       EventBus        |
                  | on(AGENT_START, fn)   |
                  | on(BLOCK_CREATED, fn) |
                  +-----------------------+
```

## Module Reference

### `block.py` -- Block and BlockHeader

`BlockHeader` is a frozen dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Zero-based position in the chain |
| `timestamp` | `str` | ISO 8601 UTC timestamp |
| `prev_hash` | `str` | SHA-256 hex digest of the preceding block |
| `agent_id` | `str` | Identifier of the agent that produced this block |
| `nonce` | `int` | Reserved for future proof-of-work or ordering schemes |

`Block` wraps a `BlockHeader` and an arbitrary `payload: dict[str, Any]`. The `block_hash` is computed on construction by applying SHA-256 to the deterministic JSON serialization (sorted keys, no whitespace) of the combined header and payload. Both dataclasses are frozen (immutable after creation).

`Block.from_dict()` performs hash verification on deserialization. `Block.genesis()` produces the initial block with `prev_hash = "0" * 64`.

### `ledger.py` -- ImmutableLedger

Append-only container for `Block` objects, initialized with a genesis block.

- `append(block)` -- validates index continuity and `prev_hash` linkage before appending. Raises `ChainIntegrityError` on mismatch.
- `validate_chain()` -- full-chain verification: index sequence, hash linkage, and per-block hash recomputation.
- `export_json()` / `from_json()` -- serialization with validation on restore. Rejects empty chains and chains with non-zero starting index.

### `agent.py` -- BaseAgent, LLMAgent, AgentResult

`BaseAgent(ABC)` requires `execute(input_data, context) -> AgentResult`. Each agent has an auto-generated unique `agent_id`.

`LLMAgent` wraps any `LLMBackend`. Context is prepended as key-value pairs to the prompt.

### `function_agent.py` -- FunctionAgent, AsyncFunctionAgent

`FunctionAgent` wraps any `Callable[[str, dict | None], str]` as a synchronous `BaseAgent`. `AsyncFunctionAgent` wraps sync or async callables for use in async pipelines.

```python
from agent_chain import FunctionAgent

def summarize(text: str, ctx=None) -> str:
    return text[:100] + "..."

agent = FunctionAgent(summarize, role="summarizer")
result = agent.execute("long text here")
```

### `pipeline.py` / `async_pipeline.py` -- AgentPipeline, AsyncPipeline

Sequential agent execution with automatic block recording and EventBus integration.

1. Agent_i receives the output of Agent_{i-1}
2. Each result is recorded as a block with truncated input/output in the payload
3. Context is updated with `prev_agent` and `prev_output`
4. Events are emitted: `PIPELINE_START`, `AGENT_START`, `AGENT_END`, `BLOCK_CREATED`, `PIPELINE_END`

`run()` resets per-run state, making pipelines safely reentrant.

### `branch_pipeline.py` -- BranchPipeline, AsyncFanOutPipeline

**BranchPipeline**: a router function `(input, context) -> branch_name` selects which named branch to execute.

```python
from agent_chain import BranchPipeline

pipeline = BranchPipeline(
    router=lambda text, ctx: "fast" if len(text) < 100 else "thorough",
    branches={
        "fast": [quick_agent],
        "thorough": [research_agent, analysis_agent],
    },
)
result = pipeline.run("short input")
```

**AsyncFanOutPipeline**: runs all branches concurrently and returns a `dict[branch_name, AgentResult]`.

### `consensus.py` / `async_consensus.py` -- ConsensusEngine, AsyncConsensusEngine

Quorum-based voting with configurable `threshold` in `(0, 1.0]`.

Vote parsing searches for APPROVE, REJECT, or ABSTAIN anywhere in the validator's response (case-insensitive). Unrecognized responses default to ABSTAIN.

`AsyncConsensusEngine` collects all validator votes concurrently via `asyncio.gather`.

### `merkle.py` -- Merkle Root

`merkle_root(hashes)` computes a standard binary Merkle tree over a list of hex hash strings. Odd-length levels duplicate the last element.

`chain_merkle_root(ledger)` computes the Merkle root over all block hashes in a ledger, providing a single 256-bit summary of the entire chain state.

### `events.py` -- EventBus

Publish/subscribe dispatcher with typed events:

| EventType | Fired by |
|-----------|----------|
| `AGENT_START` / `AGENT_END` | Pipeline, AsyncPipeline |
| `BLOCK_CREATED` | Pipeline, AsyncPipeline |
| `PIPELINE_START` / `PIPELINE_END` | Pipeline, AsyncPipeline |
| `PIPELINE_STEP` | Pipeline |
| `CONSENSUS_START` / `CONSENSUS_VOTE` | ConsensusEngine, AsyncConsensusEngine |
| `CONSENSUS_COMMIT` / `CONSENSUS_REJECT` | ConsensusEngine, AsyncConsensusEngine |

```python
from agent_chain import EventBus, EventType

bus = EventBus()
bus.on(EventType.BLOCK_CREATED, lambda et, data: print(f"Block: {data['block_hash'][:16]}"))
bus.on_all(lambda et, data: log(et.value, data))
```

### `llm/` -- LLM Backend Adapters

Synchronous backends:

| Class | Provider | API Endpoint | Auth |
|-------|----------|-------------|------|
| `OpenAIBackend` | OpenAI Chat Completions | `POST /v1/chat/completions` | `OPENAI_API_KEY` |
| `AnthropicBackend` | Anthropic Messages | `POST /v1/messages` | `ANTHROPIC_API_KEY` |
| `OllamaBackend` | Ollama local | `POST /api/generate` | None |
| `MockLLMBackend` | Deterministic mock | N/A | None |

Async backends:

| Class | Provider |
|-------|----------|
| `AsyncOpenAIBackend` | OpenAI (httpx.AsyncClient) |
| `AsyncAnthropicBackend` | Anthropic (httpx.AsyncClient) |
| `AsyncMockLLMBackend` | Deterministic async mock |
| `SyncToAsyncAdapter` | Wraps any sync `LLMBackend` for async use |

All HTTP backends support configurable `timeout`, `temperature`, `max_tokens`, and `base_url`.

## Project Structure

```
agent-chain/
    pyproject.toml
    src/
        agent_chain/
            __init__.py
            block.py
            ledger.py
            agent.py              # BaseAgent, LLMAgent
            async_agent.py        # AsyncBaseAgent, AsyncLLMAgent
            function_agent.py     # FunctionAgent, AsyncFunctionAgent
            pipeline.py           # AgentPipeline (sync)
            async_pipeline.py     # AsyncPipeline
            consensus.py          # ConsensusEngine (sync)
            async_consensus.py    # AsyncConsensusEngine
            branch_pipeline.py    # BranchPipeline, AsyncFanOutPipeline
            merkle.py             # merkle_root, chain_merkle_root
            events.py             # EventBus, EventType
            utils.py
            llm/
                __init__.py
                base.py           # LLMBackend, MockLLMBackend
                async_base.py     # AsyncLLMBackend, AsyncMockLLMBackend
                openai.py
                async_openai.py
                anthropic.py
                async_anthropic.py
                ollama.py
    examples/
        demo_pipeline.py
    tests/
        test_block.py
        test_ledger.py
        test_pipeline.py
        test_consensus.py
        test_async_pipeline.py
        test_branch_pipeline.py
        test_function_agent.py
        test_merkle.py
        test_events.py
        test_bugfixes.py
```

## Requirements

- Python >= 3.11
- Runtime: `httpx >= 0.27`
- Dev: `pytest >= 8.0`, `pytest-asyncio >= 0.23`

## Installation

```bash
git clone https://github.com/jbaelaw/agent-chain.git
cd agent-chain
pip install -e ".[dev]"
```

## Usage

### Sync Pipeline

```python
from agent_chain import AgentPipeline, ImmutableLedger, LLMAgent
from agent_chain.llm import MockLLMBackend

ledger = ImmutableLedger()
agents = [
    LLMAgent(backend=MockLLMBackend(default="research done"), role="researcher"),
    LLMAgent(backend=MockLLMBackend(default="analysis done"), role="analyst"),
]
pipeline = AgentPipeline(agents, ledger=ledger)
result = pipeline.run("investigate topic")

assert ledger.height == 3
assert ledger.validate_chain() is True
```

### Async Pipeline

```python
import asyncio
from agent_chain import AsyncPipeline, AsyncLLMAgent
from agent_chain.llm import AsyncMockLLMBackend

agents = [
    AsyncLLMAgent(backend=AsyncMockLLMBackend(default="step1"), role="a"),
    AsyncLLMAgent(backend=AsyncMockLLMBackend(default="step2"), role="b"),
]
pipeline = AsyncPipeline(agents)
result = asyncio.run(pipeline.run("start"))
```

### FunctionAgent

```python
from agent_chain import FunctionAgent, AgentPipeline

pipeline = AgentPipeline([
    FunctionAgent(lambda text, ctx: text.upper(), role="upper"),
    FunctionAgent(lambda text, ctx: f"[DONE] {text}", role="tag"),
])
result = pipeline.run("hello world")
assert result.output == "[DONE] HELLO WORLD"
```

### BranchPipeline

```python
from agent_chain import BranchPipeline

pipeline = BranchPipeline(
    router=lambda text, ctx: "short" if len(text) < 50 else "long",
    branches={"short": [fast_agent], "long": [deep_agent, review_agent]},
)
```

### Merkle Root

```python
from agent_chain import chain_merkle_root

root = chain_merkle_root(ledger)  # single 256-bit summary of entire chain
```

### EventBus

```python
from agent_chain import EventBus, EventType, AgentPipeline

bus = EventBus()
bus.on(EventType.BLOCK_CREATED, lambda et, d: print(d["block_hash"][:16]))

pipeline = AgentPipeline(agents, event_bus=bus)
pipeline.run("input")
```

## Demo

```bash
python examples/demo_pipeline.py
```

## Tests

```bash
pytest tests/ -v
```

70 tests covering block hashing, ledger integrity, sync/async pipelines, consensus, branching, function agents, Merkle trees, event bus, and regression tests for v0.1 bug fixes.

## Changelog

### v0.2.0

New features:
- `AsyncPipeline`, `AsyncConsensusEngine` with concurrent validator voting
- `AsyncLLMBackend`, `AsyncMockLLMBackend`, `AsyncOpenAIBackend`, `AsyncAnthropicBackend`, `SyncToAsyncAdapter`
- `FunctionAgent` / `AsyncFunctionAgent` for wrapping plain callables as agents
- `BranchPipeline` (conditional routing) and `AsyncFanOutPipeline` (parallel branch execution)
- `merkle_root()` / `chain_merkle_root()` for Merkle tree chain summaries
- `EventBus` with typed events integrated into Pipeline and ConsensusEngine

Bug fixes:
- `pipeline.run()` now resets per-run state (was accumulating across calls)
- `ImmutableLedger.from_json()` rejects empty chains and non-zero starting index
- `ConsensusEngine._parse_vote()` searches for keywords anywhere in output (was only checking prefix)
- Removed dead imports in `block.py` and `llm/openai.py`

### v0.1.0

Initial release with sync pipeline, consensus, immutable ledger, and LLM backends.

## License

MIT
