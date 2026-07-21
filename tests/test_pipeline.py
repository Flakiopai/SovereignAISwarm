from swarm.pipeline import Pipeline, TaskStatus


def test_submit_take_complete():
    pipe = Pipeline()
    task = pipe.submit({"text": "do thing"}, from_agent="A", to_agent="B")
    assert task.status == TaskStatus.pending
    assert len(pipe) == 1

    taken = pipe.take(agent="B")
    assert taken is not None
    assert taken.id == task.id
    assert taken.status == TaskStatus.taken

    done = pipe.complete(task.id, result={"ok": True})
    assert done.status == TaskStatus.completed
    assert done.result == {"ok": True}
    assert pipe.take(agent="B") is None


def test_take_filters_by_agent():
    pipe = Pipeline()
    pipe.submit("for-b", to_agent="B")
    pipe.submit("for-c", to_agent="C")

    taken = pipe.take(agent="C")
    assert taken is not None
    assert taken.payload == "for-c"
    assert pipe.pending(agent="B")[0].payload == "for-b"


def test_fail_and_to_dict():
    pipe = Pipeline()
    task = pipe.submit("x", task_id="custom-1")
    pipe.fail(task.id, "boom")
    assert pipe.get("custom-1").status == TaskStatus.failed
    assert pipe.get("custom-1").error == "boom"

    dumped = pipe.to_dict()
    assert dumped[0]["id"] == "custom-1"
    assert dumped[0]["status"] == "failed"


def test_duplicate_id_raises():
    pipe = Pipeline()
    pipe.submit("a", task_id="t1")
    try:
        pipe.submit("b", task_id="t1")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "already exists" in str(e)


def test_unknown_task_raises():
    pipe = Pipeline()
    try:
        pipe.get("missing")
        assert False, "expected KeyError"
    except KeyError:
        pass
