import json

from sovereignaiswarm import Swarm
from sovereignaiswarm.config import SovereignConfig
from sovereignaiswarm.conductor import Conductor
from sovereignaiswarm.llm import MockLocalLLM, create_completion

# Import the bridge module by path-friendly package-less load
import importlib.util
from pathlib import Path

BRIDGE = Path(__file__).resolve().parents[1] / "examples" / "n8n" / "run_task.py"
spec = importlib.util.spec_from_file_location("run_task", BRIDGE)
run_task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_task)


def test_run_payload_with_mock():
    mock = MockLocalLLM()
    mock.set_response(create_completion({"content": "local hello"}))
    cfg = SovereignConfig(kill_switch=False)
    conductor = Conductor(swarm=Swarm(client=mock, config=cfg), config=cfg)

    result = run_task.run_payload(
        {
            "message": "Hi",
            "agent": "Agent",
            "agents": [{"name": "Agent", "instructions": "Be brief."}],
        },
        conductor=conductor,
    )
    assert result["ok"] is True
    assert result["content"] == "local hello"
    assert result["agent"] == "Agent"


def test_main_empty_stdin_returns_error(capsys, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    code = run_task.main([])
    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["error_type"] == "ValueError"
