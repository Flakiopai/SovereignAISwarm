# Sovereign examples

These demos use Conductor, Pipeline, and FilesystemMutator against a local LLM.

## Prerequisites

```shell
ollama serve
ollama pull llama3.2
pip install -e .
```

Ensure `workspace/` exists (created automatically by the filesystem demo).

## Run

```shell
python examples/sovereign/conductor_pipeline.py
python examples/sovereign/filesystem_agent.py
```

Kill-switch: `touch .kill_switch` to halt runs; `rm .kill_switch` to resume.
