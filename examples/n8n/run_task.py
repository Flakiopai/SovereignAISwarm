#!/usr/bin/env python3
"""n8n / Docker bridge: JSON in → Swarm Conductor → JSON out.

Examples:

    echo '{"message":"Hi","agent":"Agent"}' | python examples/n8n/run_task.py

    python examples/n8n/run_task.py --file payload.json

Payload schema:

    {
      "message": "user text (required unless messages provided)",
      "messages": [{"role":"user","content":"..."}],
      "agent": "Agent",
      "agents": [
        {"name": "Agent", "instructions": "You are helpful.", "model": "llama3.2"}
      ],
      "context_variables": {},
      "model_override": null,
      "max_turns": 8
    }

Stdout is a single JSON object with ok/content/agent/messages/context_variables.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from swarm import Agent, Conductor, load_config
from swarm.config import CloudForbiddenError, KillSwitchError


def _build_agents(spec: Optional[List[dict]]) -> List[Agent]:
    if not spec:
        return [
            Agent(
                name="Agent",
                instructions="You are a helpful local agent. Keep answers concise.",
            )
        ]
    agents: List[Agent] = []
    for item in spec:
        agents.append(
            Agent(
                name=item.get("name", "Agent"),
                model=item.get("model", "llama3.2"),
                instructions=item.get(
                    "instructions", "You are a helpful local agent."
                ),
            )
        )
    return agents


def run_payload(payload: Dict[str, Any], conductor: Optional[Conductor] = None) -> Dict[str, Any]:
    """Execute one task payload and return a JSON-serializable result dict."""
    cfg = load_config()
    conductor = conductor or Conductor(config=cfg)

    agents = _build_agents(payload.get("agents"))
    for i, agent in enumerate(agents):
        conductor.register(agent, activate=(i == 0))

    agent_name = payload.get("agent") or agents[0].name
    if agent_name not in conductor.agents:
        raise KeyError(f"Unknown agent '{agent_name}'. Register it under agents[].")

    context_variables = payload.get("context_variables") or {}
    if context_variables:
        conductor.update_context(**context_variables)

    run_kwargs: Dict[str, Any] = {}
    if payload.get("model_override"):
        run_kwargs["model_override"] = payload["model_override"]
    if payload.get("max_turns") is not None:
        run_kwargs["max_turns"] = int(payload["max_turns"])

    if payload.get("messages"):
        response = conductor.delegate(
            agent_name,
            messages=list(payload["messages"]),
            **run_kwargs,
        )
    else:
        message = payload.get("message")
        if not message:
            raise ValueError("Payload requires 'message' or 'messages'")
        response = conductor.ask(str(message), agent=agent_name, **run_kwargs)

    content = None
    if response.messages:
        content = response.messages[-1].get("content")

    return {
        "ok": True,
        "content": content,
        "agent": response.agent.name if response.agent else agent_name,
        "messages": response.messages,
        "context_variables": response.context_variables,
        "state": {
            "active_agent": conductor.active_agent.name if conductor.active_agent else None,
            "agents": list(conductor.agents),
        },
    }


def _error(exc: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Swarm Sovereign n8n task bridge")
    parser.add_argument(
        "--file",
        "-f",
        help="Read JSON payload from file instead of stdin",
    )
    args = parser.parse_args(argv)

    try:
        if args.file:
            raw = open(args.file, encoding="utf-8").read()
        else:
            raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("Empty input. Provide JSON on stdin or via --file.")
        payload = json.loads(raw)
        result = run_payload(payload)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (json.JSONDecodeError, ValueError, KeyError, KillSwitchError, CloudForbiddenError) as e:
        print(json.dumps(_error(e), ensure_ascii=False))
        return 1
    except Exception as e:
        print(json.dumps(_error(e), ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
