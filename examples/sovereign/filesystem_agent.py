"""Filesystem mutator as agent tools (local Ollama).

    python examples/sovereign/filesystem_agent.py
"""

from pathlib import Path

from sovereignaiswarm import Agent, Conductor, FilesystemMutator, load_config


def main():
    cfg = load_config()
    # Ensure workspace root exists for this demo.
    Path("workspace").mkdir(exist_ok=True)
    fs = FilesystemMutator(config=cfg)

    agent = Agent(
        name="FileAgent",
        instructions=(
            "You can read and write files under allowed roots. "
            "When asked to save text, call tool_write_file. "
            "When asked to show a file, call tool_read_file."
        ),
        functions=[
            fs.tool_write_file,
            fs.tool_read_file,
            fs.tool_list_dir,
        ],
    )

    conductor = Conductor(config=cfg)
    conductor.register(agent, activate=True)

    response = conductor.ask(
        "Write the text 'sovereign-ok' to workspace/demo.txt, then read it back."
    )
    print(response.messages[-1]["content"])
    if Path("workspace/demo.txt").exists():
        print("File:", Path("workspace/demo.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
