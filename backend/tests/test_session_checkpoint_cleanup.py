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


def test_get_session_returns_checkpoint_token_stats(monkeypatch) -> None:
    checkpointer = _Checkpointer()

    class Service:
        def __init__(self, _db):
            pass

        async def get_session(self, session_id):
            return SimpleNamespace(id=session_id, to_dict=lambda: {"id": session_id})

        async def get_messages(self, _session_id):
            return []

        async def get_last_used_settings(self, _session_id):
            return {"model": None, "provider": None, "mode": None}

    async def fake_token_stats(received_checkpointer, session_id, max_tokens):
        assert received_checkpointer is checkpointer
        assert session_id == 91
        return {"current": 41848, "max": max_tokens, "percentage": 83.7}

    monkeypatch.setattr(sessions, "SessionService", Service)
    monkeypatch.setattr(sessions, "get_thread_token_stats", fake_token_stats)
    response = asyncio.run(sessions.get_session(91, _request(checkpointer), object()))

    assert response.success is True
    assert response.tokenStats["current"] == 41848
