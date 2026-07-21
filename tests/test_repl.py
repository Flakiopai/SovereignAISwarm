import json

from swarm.llm import MockLocalLLM, create_completion
from swarm.repl.repl import pretty_print_messages, process_and_print_streaming_response
from swarm.types import Response


def test_pretty_print_messages(capsys):
    messages = [
        {
            "role": "assistant",
            "sender": "Agent",
            "content": "Hello",
            "tool_calls": [
                {
                    "function": {
                        "name": "greet",
                        "arguments": json.dumps({"name": "Ada"}),
                    }
                }
            ],
        }
    ]
    pretty_print_messages(messages)
    out = capsys.readouterr().out
    assert "Agent" in out
    assert "Hello" in out
    assert "greet" in out
    assert "Ada" in out


def test_process_and_print_streaming_response(capsys):
    final = Response(
        messages=[{"role": "assistant", "content": "Hi", "sender": "Agent"}],
        agent=None,
        context_variables={},
    )
    chunks = [
        {"delim": "start"},
        {"role": "assistant", "sender": "Agent", "content": "Hi"},
        {"delim": "end"},
        {"response": final},
    ]
    result = process_and_print_streaming_response(chunks)
    out = capsys.readouterr().out
    assert "Agent" in out
    assert "Hi" in out
    assert result is final


def test_run_demo_loop_accepts_injected_client(monkeypatch):
    from swarm import Agent, Swarm
    from swarm.config import SovereignConfig
    from swarm.repl import run_demo_loop

    mock = MockLocalLLM()
    mock.set_response(create_completion({"content": "pong"}))
    client = Swarm(client=mock, config=SovereignConfig(kill_switch=False))

    calls = {"n": 0}

    def fake_input(_prompt=""):
        calls["n"] += 1
        if calls["n"] == 1:
            return "ping"
        raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)
    run_demo_loop(Agent(name="Ping"), client=client)
    assert calls["n"] == 2
