# Swarm Sovereign

Local-first, offline-capable multi-agent orchestration — a sovereign fork of OpenAI Swarm.

Maintained by MatteBlackStudios

## What changed

| Upstream Swarm | Swarm Sovereign |
|----------------|-----------------|
| OpenAI Chat Completions | Local Ollama-compatible HTTP client |
| `openai` SDK dependency | `pydantic` only |
| Unbounded client-side runs | Sovereign config: privacy, kill-switch, turn ceiling |
| Handoffs only | + Pipeline, Conductor, safe FilesystemMutator |

Public API stays compatible:

```python
from swarm import Swarm, Agent
```

## Install

Python 3.10+

```shell
pip install -e ".[dev]"
```

Local model server (Ollama):

```shell
ollama serve
ollama pull llama3.2
```

Defaults: `http://127.0.0.1:11434/v1`, model `llama3.2`.

Override with env:

- `SWARM_LLM_BASE_URL`
- `SWARM_LLM_MODEL`
- `SOVEREIGN_CONFIG` (path to YAML)

## Quickstart

```python
from swarm import Swarm, Agent

client = Swarm()

agent = Agent(
    name="Agent",
    instructions="You are a helpful agent.",
)

response = client.run(
    agent=agent,
    messages=[{"role": "user", "content": "Hi!"}],
)
print(response.messages[-1]["content"])
```

Handoffs, tools, and `context_variables` work as in upstream Swarm.

### REPL

```python
from swarm import Agent
from swarm.repl import run_demo_loop

run_demo_loop(Agent(instructions="You are a helpful agent."))
```

## Sovereign config

`sovereign.yaml` (repo root) or path in `SOVEREIGN_CONFIG`:

```yaml
allow_cloud: false
kill_switch: true
kill_switch_path: .kill_switch
default_model: llama3.2
llm_base_url: http://127.0.0.1:11434/v1
max_turns: 20
allowed_roots:
  - ./workspace
  - ./examples
```

```python
from swarm import load_config

cfg = load_config()
cfg.assert_llm_allowed(cfg.llm_base_url)  # blocks cloud URLs when allow_cloud is false
cfg.assert_not_killed()                   # raises if .kill_switch exists
```

| Rule | Behavior |
|------|----------|
| `allow_cloud: false` | Non-local LLM URLs raise `CloudForbiddenError` |
| Kill-switch | Create `.kill_switch` to halt `Swarm.run` / Conductor / filesystem ops |
| `max_turns` | Ceiling applied to `client.run(...)` |
| `allowed_roots` | Sandbox for `FilesystemMutator` |

## Modules

### Filesystem (safe)

```python
from swarm import FilesystemMutator

fs = FilesystemMutator()
fs.write("workspace/out.txt", "hello")
print(fs.read("workspace/out.txt"))
```

Paths must resolve under `allowed_roots`. Delete is off unless `allow_delete=True`.
Agent tool wrappers: `tool_read_file`, `tool_write_file`, `tool_list_dir`.

### Pipeline

In-memory task queue for agent ↔ agent (or n8n node ↔ node) handoff:

```python
from swarm import Pipeline

pipe = Pipeline()
pipe.submit({"job": "summarize"}, from_agent="intake", to_agent="writer")
task = pipe.take(agent="writer")
pipe.complete(task.id, result="done")
```

### Conductor

Named agents, shared history/context, optional pipeline processing:

```python
from swarm import Agent, Conductor

conductor = Conductor()
conductor.register(Agent(name="Writer", instructions="Be concise."), activate=True)
response = conductor.ask("Summarize sovereignty in one sentence.")
print(response.messages[-1]["content"])
```

## n8n / Docker

JSON stdin (or `--file`) → stdout:

```shell
echo '{"message":"Say hello in five words.","agent":"Agent"}' \
  | python examples/n8n/run_task.py
```

```shell
python examples/n8n/run_task.py --file examples/n8n/sample_payload.json
```

Success shape:

```json
{
  "ok": true,
  "content": "...",
  "agent": "Agent",
  "messages": [],
  "context_variables": {},
  "state": {"active_agent": "Agent", "agents": ["Agent"]}
}
```

See `examples/n8n/README.md` for Execute Command / Compose wiring.

## Examples

| Path | Purpose |
|------|---------|
| `examples/basic/` | Upstream-style API demos + REPL |
| `examples/sovereign/` | Conductor, Pipeline, FilesystemMutator |
| `examples/n8n/` | Workflow bridge |

## Layout

```text
swarm/
  core.py          # Swarm.run (public API)
  types.py         # Agent, Response, Result
  llm.py           # LocalLLM (Ollama-compatible)
  config.py        # SovereignConfig
  filesystem.py    # FilesystemMutator
  pipeline.py      # Task queue
  conductor.py     # Registry + delegation
  util.py
  repl/
sovereign.yaml
examples/
tests/
```

## Tests

```shell
pip install -e ".[dev]"
pytest -q
```

## License

MIT — derived from OpenAI Swarm. See `LICENSE`.
