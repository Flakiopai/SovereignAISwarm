from sovereignaiswarm import Agent, Response, Result
from sovereignaiswarm.types import (
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
    Function,
)


def test_agent_defaults_to_local_model():
    agent = Agent()
    assert agent.name == "Agent"
    assert agent.model == "llama3.2"
    assert agent.functions == []
    assert agent.tool_choice is None


def test_agent_accepts_callable_instructions_and_functions():
    def instructions():
        return "Be brief."

    def handoff():
        return Agent(name="B")

    agent = Agent(name="A", instructions=instructions, functions=[handoff])
    assert callable(agent.instructions)
    assert agent.functions[0].__name__ == "handoff"


def test_response_and_result_defaults():
    response = Response()
    assert response.messages == []
    assert response.agent is None
    assert response.context_variables == {}

    result = Result(value="ok", context_variables={"k": "v"})
    assert result.value == "ok"
    assert result.agent is None
    assert result.context_variables == {"k": "v"}


def test_local_message_types_have_no_cloud_sdk_dependency():
    tool_call = ChatCompletionMessageToolCall(
        id="tc1",
        function=Function(name="greet", arguments='{"name":"Ada"}'),
    )
    message = ChatCompletionMessage(
        content="hi",
        role="assistant",
        tool_calls=[tool_call],
        sender="Agent",
    )
    assert message.sender == "Agent"
    assert message.tool_calls[0].function.name == "greet"
