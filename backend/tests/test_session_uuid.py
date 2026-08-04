import asyncio
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import Base, _initialize_schema
from app.services.session_service import SessionService
from app.services.utils import generate_uuid7, normalize_uuid


def test_generate_uuid7_returns_valid_time_ordered_uuid() -> None:
    first = generate_uuid7()
    second = generate_uuid7()

    assert uuid.UUID(first).version == 7
    assert uuid.UUID(second).version == 7
    assert first != second
    assert normalize_uuid(first.upper()) == first
    assert normalize_uuid("1") is None


def test_session_service_exposes_uuid_and_keeps_internal_message_fk(tmp_path) -> None:
    async def run() -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'sessions.db'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            service = SessionService(db)
            session = await service.create_session()
            session_id = session.id
            message = await service.add_message(session_id, "user", "UUID 会话")
            await db.commit()

            assert uuid.UUID(session_id).version == 7
            assert isinstance(session.db_id, int)
            assert message is not None
            assert message.session_id == session.db_id
            assert (await service.get_session(session_id)).db_id == session.db_id
            assert [item.content for item in await service.get_messages(session_id)] == ["UUID 会话"]

        await engine.dispose()

    asyncio.run(run())


def test_legacy_integer_sessions_are_backfilled_with_uuid(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE sessions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title VARCHAR(255), preview TEXT, created_at DATETIME, updated_at DATETIME)"
        )
        connection.exec_driver_sql("INSERT INTO sessions (title) VALUES ('旧会话一'), ('旧会话二')")
        _initialize_schema(connection)
        values = connection.execute(text("SELECT session_uuid FROM sessions ORDER BY id")).scalars().all()

    assert len(values) == 2
    assert len(set(values)) == 2
    assert all(uuid.UUID(value).version == 7 for value in values)
    engine.dispose()
