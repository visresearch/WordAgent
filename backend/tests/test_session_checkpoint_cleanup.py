import asyncio
from types import SimpleNamespace

from app.api.routes import sessions


class _Checkpointer:
    def __init__(self):
        self.deleted: list[str] = []

    async def adelete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


def _request(checkpointer: _Checkpointer):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(checkpointer=checkpointer)))


def test_single_agent_delete_session_deletes_checkpoint(monkeypatch) -> None:
    checkpointer = _Checkpointer()

    class Service:
        def __init__(self, _db):
            pass

        async def get_session(self, session_id):
            return SimpleNamespace(id=session_id)

        async def delete_session(self, _session_id):
            return True

    monkeypatch.setattr(sessions, "SessionService", Service)
    response = asyncio.run(sessions.delete_session(71, _request(checkpointer), object()))

    assert response.success is True
    assert checkpointer.deleted == ["session:71"]


def test_single_agent_clear_messages_deletes_checkpoint(monkeypatch) -> None:
    checkpointer = _Checkpointer()

    class Service:
        def __init__(self, _db):
            pass

        async def get_session(self, session_id):
            return SimpleNamespace(id=session_id)

        async def clear_session_messages(self, _session_id):
            return True

    monkeypatch.setattr(sessions, "SessionService", Service)
    response = asyncio.run(sessions.clear_session_messages(72, _request(checkpointer), object()))

    assert response.success is True
    assert checkpointer.deleted == ["session:72"]


def test_clear_all_sessions_deletes_every_checkpoint_first(monkeypatch) -> None:
    checkpointer = _Checkpointer()

    class Service:
        def __init__(self, _db):
            pass

        async def get_all_session_ids(self):
            return [81, 82]

        async def clear_all_sessions(self):
            assert checkpointer.deleted == ["session:81", "session:82"]
            return 4

    monkeypatch.setattr(sessions, "SessionService", Service)
    response = asyncio.run(sessions.clear_all_sessions(_request(checkpointer), object()))

    assert response.success is True
    assert checkpointer.deleted == ["session:81", "session:82"]
