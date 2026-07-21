import json

import pytest

from swarm.llm import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LocalLLM,
    MockLocalLLM,
    chunk_from_dict,
    completion_from_dict,
    create_completion,
)


def test_local_llm_defaults_from_env(monkeypatch):
    monkeypatch.delenv("SWARM_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SWARM_LLM_MODEL", raising=False)
    client = LocalLLM(enforce_config=False)
    assert client.base_url == DEFAULT_BASE_URL
    assert client.model == DEFAULT_MODEL


def test_local_llm_reads_env(monkeypatch):
    monkeypatch.setenv("SWARM_LLM_BASE_URL", "http://127.0.0.1:9999/v1/")
    monkeypatch.setenv("SWARM_LLM_MODEL", "mistral")
    client = LocalLLM(enforce_config=False)
    assert client.base_url == "http://127.0.0.1:9999/v1"
    assert client.model == "mistral"


def test_local_llm_blocks_cloud_url_by_default():
    from swarm.config import CloudForbiddenError

    with pytest.raises(CloudForbiddenError):
        LocalLLM(base_url="https://api.openai.com/v1")


def test_completion_from_dict_parses_tool_calls():
    data = {
        "id": "cmp_1",
        "model": "llama3.2",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "tc_1",
                            "type": "function",
                            "function": {
                                "name": "greet",
                                "arguments": '{"name":"Ada"}',
                            },
                        }
                    ],
                },
            }
        ],
    }
    completion = completion_from_dict(data)
    message = completion.choices[0].message
    assert message.tool_calls is not None
    assert message.tool_calls[0].function.name == "greet"
    assert json.loads(message.tool_calls[0].function.arguments)["name"] == "Ada"
    dumped = json.loads(message.model_dump_json())
    assert dumped["tool_calls"][0]["function"]["name"] == "greet"


def test_chunk_from_dict_exposes_json_delta():
    chunk = chunk_from_dict(
        {
            "id": "chk_1",
            "model": "llama3.2",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "Hi"},
                }
            ],
        }
    )
    delta = json.loads(chunk.choices[0].delta.json())
    assert delta["content"] == "Hi"
    assert delta["role"] == "assistant"


def test_mock_local_llm_sequential_responses():
    client = MockLocalLLM()
    client.set_sequential_responses(
        [
            create_completion(
                {"role": "assistant", "content": "First"},
                [{"name": "process_refund", "args": {"item_id": "item_123"}}],
            ),
            create_completion({"role": "assistant", "content": "Second"}),
        ]
    )

    first = client.chat.completions.create(
        model="llama3.2",
        messages=[{"role": "user", "content": "refund"}],
        tools=[{"type": "function", "function": {"name": "process_refund"}}],
    )
    second = client.chat.completions.create(
        model="llama3.2",
        messages=[{"role": "user", "content": "ok"}],
    )

    assert first.choices[0].message.content == "First"
    assert first.choices[0].message.tool_calls[0].function.name == "process_refund"
    assert second.choices[0].message.content == "Second"
    assert client.last_create_kwargs()["model"] == "llama3.2"


def test_create_completion_helper_sets_finish_reason():
    with_tools = create_completion(
        {"content": None},
        [{"name": "f", "args": {}}],
    )
    without = create_completion({"content": "hi"})
    assert with_tools.choices[0].finish_reason == "tool_calls"
    assert without.choices[0].finish_reason == "stop"
