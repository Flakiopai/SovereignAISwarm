from typing import Callable, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


AgentFunction = Callable[..., Union[str, "Agent", dict]]


class Function(BaseModel):
    """Local stand-in for an OpenAI function call payload."""

    arguments: str
    name: str


class ChatCompletionMessageToolCall(BaseModel):
    """Local stand-in for a Chat Completions tool call."""

    id: str
    function: Function
    type: str = "function"


class ChatCompletionMessage(BaseModel):
    """Local stand-in for a Chat Completions message."""

    content: Optional[str] = None
    role: str = "assistant"
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    sender: Optional[str] = None


class Agent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Agent"
    model: str = "llama3.2"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = Field(default_factory=list)
    tool_choice: Optional[str] = None
    parallel_tool_calls: bool = True


class Response(BaseModel):
    messages: List = Field(default_factory=list)
    agent: Optional[Agent] = None
    context_variables: dict = Field(default_factory=dict)


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.

    Attributes:
        value: The result value as a string.
        agent: The agent instance, if applicable.
        context_variables: A dictionary of context variables.
    """

    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = Field(default_factory=dict)
