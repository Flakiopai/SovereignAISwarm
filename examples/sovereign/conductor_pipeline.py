"""Conductor + Pipeline demo (local Ollama).

    python examples/sovereign/conductor_pipeline.py
"""

from swarm import Agent, Conductor


def main():
    conductor = Conductor()

    intake = Agent(
        name="Intake",
        instructions="You acknowledge tasks briefly and confirm what you received.",
    )
    writer = Agent(
        name="Writer",
        instructions="You rewrite the user text as one clear sentence. No preamble.",
    )
    conductor.register(intake, activate=True)
    conductor.register(writer)

    # Stage 1: intake agent
    first = conductor.ask("Draft a short note about local-first agents.")
    print("Intake:", first.messages[-1]["content"])

    # Stage 2: hand off via pipeline to writer
    content = first.messages[-1]["content"]
    conductor.enqueue({"content": content}, to_agent="Writer", from_agent="Intake")
    second = conductor.process_next(agent="Writer")
    print("Writer:", second.messages[-1]["content"])
    print("State agents:", conductor.state()["agents"])


if __name__ == "__main__":
    main()
