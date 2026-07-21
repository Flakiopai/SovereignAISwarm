# n8n Docker bridge

Run SovereignAISwarm as an Execute Command / Docker step. JSON in, JSON out.

## Quick test

Install, then pipe a JSON payload on stdin:

```shell
pip install -e .

echo '{"message":"Say hello in five words.","agent":"Agent"}' \
  | python examples/n8n/run_task.py
```

Or load a payload from a file:

```shell
python examples/n8n/run_task.py --file examples/n8n/sample_payload.json
```

## n8n Execute Command node

Command example (host has the repo and a local Ollama server):

```text
python /path/to/SovereignAISwarm/examples/n8n/run_task.py
```

Set the node to pass JSON on stdin (or write a temp file and use `--file`).

Parse stdout as JSON and read the `content` and `ok` fields.

## Docker Compose sketch

Example services for a local model server and a Python worker:

```yaml
services:
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]

  sovereignaiswarm:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - ./:/app
    environment:
      SWARM_LLM_BASE_URL: http://ollama:11434/v1
      SWARM_LLM_MODEL: llama3.2
    command: sleep infinity
```

Then from an n8n command node against the `sovereignaiswarm` container:

```text
python examples/n8n/run_task.py --file /data/payload.json
```

## Kill-switch

If `.kill_switch` exists in the working directory, the bridge returns
`{"ok": false, "error_type": "KillSwitchError", ...}` as plain JSON text
(no color-only signaling).
