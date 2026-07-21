from sovereignaiswarm import Agent, Swarm
from sovereignaiswarm.config import SovereignConfig
from sovereignaiswarm.conductor import Conductor
from sovereignaiswarm.llm import MockLocalLLM, create_completion
from sovereignaiswarm.pipeline import TaskStatus


def _conductor_with_mock(responses):
    mock = MockLocalLLM()
    mock.set_sequential_responses(responses)
    cfg = SovereignConfig(kill_switch=False, max_turns=10)
    swarm = Swarm(client=mock, config=cfg)
    return Conductor(swarm=swarm, config=cfg), mock


def test_register_and_delegate():
    conductor, _mock = _conductor_with_mock(
        [create_completion({"content": "hello from A"})]
    )
    agent_a = Agent(name="A", instructions="Agent A")
    conductor.register(agent_a, activate=True)

    response = conductor.delegate(
        "A",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert response.messages[-1]["content"] == "hello from A"
    assert conductor.active_agent.name == "A"
    assert conductor.messages[-1]["content"] == "hello from A"


def test_ask_appends_history():
    conductor, _mock = _conductor_with_mock(
        [
            create_completion({"content": "one"}),
            create_completion({"content": "two"}),
        ]
    )
    conductor.register(Agent(name="Bot"), activate=True)

    conductor.ask("first")
    conductor.ask("second")

    roles = [m["role"] for m in conductor.messages]
    assert roles.count("user") == 2
    assert conductor.messages[-1]["content"] == "two"


def test_handoff_updates_active_agent():
    def transfer_to_b():
        return agent_b

    agent_a = Agent(name="A", functions=[transfer_to_b])
    agent_b = Agent(name="B")

    conductor, _mock = _conductor_with_mock(
        [
            create_completion(
                {"content": ""},
                [{"name": "transfer_to_b"}],
            ),
            create_completion({"content": "now with B"}),
        ]
    )
    conductor.register(agent_a, activate=True)
    conductor.register(agent_b)

    response = conductor.ask("switch")
    assert response.agent.name == "B"
    assert conductor.active_agent.name == "B"
    assert "B" in conductor.agents


def test_pipeline_enqueue_and_process_next():
    conductor, _mock = _conductor_with_mock(
        [create_completion({"content": "processed"})]
    )
    conductor.register(Agent(name="Writer"), activate=True)

    task = conductor.enqueue({"content": "write this"}, to_agent="Writer")
    assert task.status == TaskStatus.pending

    response = conductor.process_next(agent="Writer")
    assert response is not None
    assert response.messages[-1]["content"] == "processed"
    assert conductor.pipeline.get(task.id).status == TaskStatus.completed
    assert conductor.pipeline.get(task.id).result == "processed"


def test_process_next_returns_none_when_empty():
    conductor, _mock = _conductor_with_mock([])
    conductor.register(Agent(name="Writer"), activate=True)
    assert conductor.process_next("Writer") is None


def test_state_snapshot():
    conductor, _mock = _conductor_with_mock(
        [create_completion({"content": "ok"})]
    )
    conductor.register(Agent(name="A"), activate=True)
    conductor.update_context(user="Ada")
    conductor.ask("hi")
    snap = conductor.state()
    assert snap["active_agent"] == "A"
    assert snap["context_variables"]["user"] == "Ada"
    assert snap["messages"]
