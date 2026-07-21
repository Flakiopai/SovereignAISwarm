"""Conductor: agent registry, conversation state, and delegation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .config import SovereignConfig, load_config
from .core import Swarm
from .pipeline import Pipeline, Task
from .types import Agent, Response


class Conductor:
    """
    Thin orchestration layer on top of Swarm.

    Does not replace handoffs — sits above them for named delegation,
    shared context, and optional Pipeline integration.
    """

    def __init__(
        self,
        swarm: Optional[Swarm] = None,
        pipeline: Optional[Pipeline] = None,
        config: Optional[SovereignConfig] = None,
    ):
        self.config = config or load_config()
        self.swarm = swarm or Swarm(config=self.config)
        self.pipeline = pipeline if pipeline is not None else Pipeline()
        self.agents: Dict[str, Agent] = {}
        self.active_agent: Optional[Agent] = None
        self.messages: List[dict] = []
        self.context_variables: Dict[str, Any] = {}

    def register(self, agent: Agent, *, activate: bool = False) -> Agent:
        if not agent.name:
            raise ValueError("Agent must have a name to register")
        self.agents[agent.name] = agent
        if activate or self.active_agent is None:
            self.active_agent = agent
        return agent

    def get(self, name: str) -> Agent:
        try:
            return self.agents[name]
        except KeyError as e:
            raise KeyError(f"Unknown agent: {name}. Known: {list(self.agents)}") from e

    def set_active(self, name: str) -> Agent:
        agent = self.get(name)
        self.active_agent = agent
        return agent

    def update_context(self, **kwargs: Any) -> Dict[str, Any]:
        self.context_variables.update(kwargs)
        return self.context_variables

    def delegate(
        self,
        agent: Union[str, Agent],
        messages: Optional[List[dict]] = None,
        *,
        context_variables: Optional[dict] = None,
        append_history: bool = True,
        **run_kwargs: Any,
    ) -> Response:
        """Run Swarm against a named (or Agent) target and update conductor state."""
        self.config.assert_not_killed()
        target = agent if isinstance(agent, Agent) else self.get(agent)
        if target.name not in self.agents:
            self.register(target)

        msgs = list(messages) if messages is not None else list(self.messages)
        ctx = {
            **self.context_variables,
            **(context_variables or {}),
        }

        response = self.swarm.run(
            agent=target,
            messages=msgs,
            context_variables=ctx,
            **run_kwargs,
        )

        if append_history:
            self.messages = msgs + list(response.messages)

        self.context_variables.update(response.context_variables or {})
        if response.agent is not None:
            self.active_agent = response.agent
            if response.agent.name not in self.agents:
                self.register(response.agent)

        return response

    def ask(
        self,
        content: str,
        agent: Optional[Union[str, Agent]] = None,
        **run_kwargs: Any,
    ) -> Response:
        """Append a user message and delegate to the active (or named) agent."""
        target = agent if agent is not None else self.active_agent
        if target is None:
            raise RuntimeError("No active agent. register(...) first.")
        messages = list(self.messages) + [{"role": "user", "content": content}]
        return self.delegate(target, messages=messages, **run_kwargs)

    def enqueue(
        self,
        payload: Any,
        *,
        to_agent: str,
        from_agent: Optional[str] = None,
    ) -> Task:
        source = from_agent or (self.active_agent.name if self.active_agent else None)
        return self.pipeline.submit(
            payload,
            from_agent=source,
            to_agent=to_agent,
        )

    def process_next(
        self,
        agent: Optional[str] = None,
        *,
        message_key: str = "content",
        **run_kwargs: Any,
    ) -> Optional[Response]:
        """
        Take the next pipeline task for an agent, run it, complete/fail the task.

        Payload may be a string or a dict containing `message_key`.
        """
        self.config.assert_not_killed()
        name = agent or (self.active_agent.name if self.active_agent else None)
        if not name:
            raise RuntimeError("No agent specified and no active agent set.")

        task = self.pipeline.take(agent=name)
        if task is None:
            return None

        try:
            if isinstance(task.payload, dict):
                content = task.payload.get(message_key, task.payload)
                content = content if isinstance(content, str) else str(content)
            else:
                content = str(task.payload)

            response = self.ask(content, agent=name, **run_kwargs)
            last = response.messages[-1]["content"] if response.messages else None
            self.pipeline.complete(task.id, result=last)
            return response
        except Exception as e:
            self.pipeline.fail(task.id, error=str(e))
            raise

    def state(self) -> dict:
        return {
            "active_agent": self.active_agent.name if self.active_agent else None,
            "agents": list(self.agents),
            "messages": list(self.messages),
            "context_variables": dict(self.context_variables),
            "pipeline": self.pipeline.to_dict(),
        }
