"""Minimal interactive REPL example.

Requires a local Ollama-compatible server.

    python examples/basic/repl_demo.py
"""

from sovereignaiswarm import Agent
from sovereignaiswarm.repl import run_demo_loop

agent = Agent(
    name="Agent",
    instructions="You are a helpful agent. Keep answers brief.",
)

if __name__ == "__main__":
    run_demo_loop(agent)
