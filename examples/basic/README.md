# Basic examples

Same public Swarm API as the Swarm educational framework / upstream Swarm.
Runs against a local Ollama server by default.

## Prerequisites

Start a local model server:

```shell
ollama serve
ollama pull llama3.2
```

Install this package editable:

```shell
pip install -e .
```

## Run

Each script below is a short demonstration of agents, tools, or handoffs:

```shell
python examples/basic/bare_minimum.py
python examples/basic/function_calling.py
python examples/basic/agent_handoff.py
python examples/basic/context_variables.py
python examples/basic/repl_demo.py
```

The REPL demo reads from stdin (keyboard or pipe). Exit with Ctrl-C or EOF.
Set `NO_COLOR=1` if you prefer plain-text labels without ANSI colors.
