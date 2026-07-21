import json
from unittest.mock import Mock

import pytest

from swarm import Agent, Swarm
from swarm.config import KillSwitchError, SovereignConfig
from swarm.llm import MockLocalLLM, create_completion

DEFAULT_RESPONSE_CONTENT = "sample response content"


@pytest.fixture
def mock_llm():
    m = MockLocalLLM()
    m.set_response(
        create_completion({"role": "assistant", "content": DEFAULT_RESPONSE_CONTENT})
    )
    return m


@pytest.fixture
def config():
    return SovereignConfig(max_turns=20, kill_switch=False)


def test_run_with_simple_message(mock_llm, config):
    agent = Agent()
    client = Swarm(client=mock_llm, config=config)
    messages = [{"role": "user", "content": "Hello, how are you?"}]
    response = client.run(agent=agent, messages=messages)

    assert response.messages[-1]["role"] == "assistant"
    assert response.messages[-1]["content"] == DEFAULT_RESPONSE_CONTENT
    assert response.messages[-1]["sender"] == "Agent"


def test_tool_call(mock_llm, config):
    expected_location = "San Francisco"
    get_weather_mock = Mock()

    def get_weather(location):
        get_weather_mock(location=location)
        return "It's sunny today."

    agent = Agent(name="Test Agent", functions=[get_weather])
    messages = [
        {"role": "user", "content": "What's the weather like in San Francisco?"}
    ]

    mock_llm.set_sequential_responses(
        [
            create_completion(
                {"role": "assistant", "content": ""},
                [{"name": "get_weather", "args": {"location": expected_location}}],
            ),
            create_completion({"role": "assistant", "content": DEFAULT_RESPONSE_CONTENT}),
        ]
    )

    client = Swarm(client=mock_llm, config=config)
    response = client.run(agent=agent, messages=messages)

    get_weather_mock.assert_called_once_with(location=expected_location)
    assert response.messages[-1]["role"] == "assistant"
    assert response.messages[-1]["content"] == DEFAULT_RESPONSE_CONTENT


def test_execute_tools_false(mock_llm, config):
    expected_location = "San Francisco"
    get_weather_mock = Mock()

    def get_weather(location):
        get_weather_mock(location=location)
        return "It's sunny today."

    agent = Agent(name="Test Agent", functions=[get_weather])
    messages = [
        {"role": "user", "content": "What's the weather like in San Francisco?"}
    ]

    mock_llm.set_sequential_responses(
        [
            create_completion(
                {"role": "assistant", "content": ""},
                [{"name": "get_weather", "args": {"location": expected_location}}],
            ),
            create_completion({"role": "assistant", "content": DEFAULT_RESPONSE_CONTENT}),
        ]
    )

    client = Swarm(client=mock_llm, config=config)
    response = client.run(agent=agent, messages=messages, execute_tools=False)

    get_weather_mock.assert_not_called()
    tool_calls = response.messages[-1].get("tool_calls")
    assert tool_calls is not None and len(tool_calls) == 1
    tool_call = tool_calls[0]
    assert tool_call["function"]["name"] == "get_weather"
    assert json.loads(tool_call["function"]["arguments"]) == {
        "location": expected_location
    }


def test_handoff(mock_llm, config):
    def transfer_to_agent2():
        return agent2

    agent1 = Agent(name="Test Agent 1", functions=[transfer_to_agent2])
    agent2 = Agent(name="Test Agent 2")

    mock_llm.set_sequential_responses(
        [
            create_completion(
                {"role": "assistant", "content": ""},
                [{"name": "transfer_to_agent2"}],
            ),
            create_completion({"role": "assistant", "content": DEFAULT_RESPONSE_CONTENT}),
        ]
    )

    client = Swarm(client=mock_llm, config=config)
    messages = [{"role": "user", "content": "I want to talk to agent 2"}]
    response = client.run(agent=agent1, messages=messages)

    assert response.agent == agent2
    assert response.messages[-1]["role"] == "assistant"
    assert response.messages[-1]["content"] == DEFAULT_RESPONSE_CONTENT


def test_kill_switch_halts_run(mock_llm, tmp_path):
    flag = tmp_path / ".kill_switch"
    flag.write_text("stop\n", encoding="utf-8")
    cfg = SovereignConfig(kill_switch=True, kill_switch_path=str(flag))
    client = Swarm(client=mock_llm, config=cfg)

    with pytest.raises(KillSwitchError):
        client.run(
            agent=Agent(),
            messages=[{"role": "user", "content": "hi"}],
        )


def test_max_turns_capped_by_config(mock_llm, config):
    config.max_turns = 1
    # Would loop forever without a cap: always returns a tool call.
    def noop():
        return "ok"

    agent = Agent(functions=[noop])
    mock_llm.set_response(
        create_completion(
            {"role": "assistant", "content": ""},
            [{"name": "noop"}],
        )
    )
    client = Swarm(client=mock_llm, config=config)
    response = client.run(
        agent=agent,
        messages=[{"role": "user", "content": "go"}],
        max_turns=float("inf"),
    )
    # One model turn (+ tool message) then stop due to ceiling.
    assert any(m.get("role") == "assistant" for m in response.messages)
