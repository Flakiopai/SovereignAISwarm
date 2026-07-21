import json
import os

from sovereignaiswarm import Swarm


def _use_color() -> bool:
    """ANSI color is decorative only; respect NO_COLOR / FORCE_COLOR."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return True


def _paint(text: str, code: str) -> str:
    if not _use_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def process_and_print_streaming_response(response):
    content = ""
    last_sender = ""

    for chunk in response:
        if "sender" in chunk:
            last_sender = chunk["sender"]

        if "content" in chunk and chunk["content"] is not None:
            if not content and last_sender:
                print(f"{_paint(last_sender, '94')}:", end=" ", flush=True)
                last_sender = ""
            print(chunk["content"], end="", flush=True)
            content += chunk["content"]

        if "tool_calls" in chunk and chunk["tool_calls"] is not None:
            for tool_call in chunk["tool_calls"]:
                f = tool_call["function"]
                name = f["name"]
                if not name:
                    continue
                print(f"{_paint(last_sender, '94')}: {_paint(name, '95')}()")

        if "delim" in chunk and chunk["delim"] == "end" and content:
            print()  # End of response message
            content = ""

        if "response" in chunk:
            return chunk["response"]


def pretty_print_messages(messages) -> None:
    for message in messages:
        if message["role"] != "assistant":
            continue

        print(f"{_paint(message['sender'], '94')}:", end=" ")

        if message["content"]:
            print(message["content"])

        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"{_paint(name, '95')}({arg_str[1:-1]})")


def run_demo_loop(
    starting_agent,
    context_variables=None,
    stream=False,
    debug=False,
    client=None,
) -> None:
    """Interactive CLI loop. Uses a local Swarm client by default.

    Input is plain stdin (keyboard / pipe). Ctrl-C or EOF exits cleanly.
    Set `NO_COLOR=1` to disable decorative ANSI colors; labels remain text-only.
    """
    client = client or Swarm()
    print("Starting SovereignAISwarm CLI")
    if not _use_color():
        print("(NO_COLOR enabled — labels are plain text)")

    messages = []
    agent = starting_agent

    while True:
        try:
            user_input = input(f"{_paint('User', '90')}: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        messages.append({"role": "user", "content": user_input})

        response = client.run(
            agent=agent,
            messages=messages,
            context_variables=context_variables or {},
            stream=stream,
            debug=debug,
        )

        if stream:
            response = process_and_print_streaming_response(response)
        else:
            pretty_print_messages(response.messages)

        messages.extend(response.messages)
        agent = response.agent
