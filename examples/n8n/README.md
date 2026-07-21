# n8n Docker bridge

Run Swarm Sovereign as an Execute Command / Docker step. JSON in, JSON out.

## Quick test

```shell
pip install -e .

echo '{"message":"Say hello in five words.","agent":"Agent"}' \
  | python examples/n8n/run_task.py
```

Custom agents:

```shell
python examples/n8n/run_task.py --file examples/n8n/sample_payload.json
```

## n8n Execute Command node

Command example (host has the repo + Ollama):

```text
python /path/to/OpenAISwarmSovereign/examples/n8n/run_task.py
```

Set the node to pass JSON on stdin (or write a temp file and use `--file`).

Parse stdout as JSON and read `content` / `ok`.

## Docker Compose sketch

```yaml
services:
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]

  swarm:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - ./:/app
    environment:
      SWARM_LLM_BASE_URL: http://ollama:11434/v1
      SWARM_LLM_MODEL: llama3.2
    command: sleep infinity
```

Then from an n8n command node against the `swarm` container:

```text
python examples/n8n/run_task.py --file /data/payload.json
```

## Kill-switch

If `.kill_switch` exists in the working directory, the bridge returns
`{"ok": false, "error_type": "KillSwitchError", ...}`.
