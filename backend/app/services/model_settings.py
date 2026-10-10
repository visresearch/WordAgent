"""SQLite persistence and migration for per-provider model parameters."""

import json
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import create_engine, delete, select, tuple_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool

from app.core.config import get_user_settings_file, settings
from app.core.logging import get_logger
from app.models.db_models import ModelParameterConfig
from app.models.model_config import ModelParameters

logger = get_logger(__name__)
# Inference constructs synchronous LangChain clients, so use a synchronous
# connection to the same SQLite database as the asynchronous application engine.
engine = create_engine(make_url(settings.database_url).set(drivername="sqlite"), poolclass=NullPool)
table = ModelParameterConfig.__table__


def provider_key(name: str) -> str:
    return name.strip().casefold()


def normalize_legacy_parameters(parameters=None, temperature=0.5) -> dict:
    """Retain valid legacy values and fill missing/invalid values independently."""
    raw = parameters if isinstance(parameters, dict) else {}
    result = ModelParameters().model_dump()
    for key in result:
        value = raw.get(key, temperature if key == "temperature" else result[key])
        with suppress(ValidationError):
            result[key] = getattr(ModelParameters.model_validate({key: value}), key)
    return result


def _rows_to_parameters(rows) -> dict:
    return {
        (row.provider_name, row.model_id): {
            "temperature": row.temperature,
            "topP": row.top_p,
            "maxTokens": row.max_tokens,
            "reasoningEffort": row.reasoning_effort,
        }
        for row in rows
    }


def load_model_parameters() -> dict:
    try:
        with engine.connect() as connection:
            return _rows_to_parameters(connection.execute(select(table)))
    except OperationalError as error:
        # Permit legacy settings before startup has created the new table.
        if "no such table: model_parameters" in str(error):
            return {}
        raise


def enrich_providers(providers: list[dict], stored: dict, legacy_temperature=0.5) -> list[dict]:
    return [
        {
            **provider,
            "models": [
                {
                    **model,
                    "parameters": stored.get((provider_key(provider["name"]), model["id"]))
                    or normalize_legacy_parameters(model.get("parameters"), legacy_temperature),
                }
                for model in provider.get("models", [])
            ],
        }
        for provider in providers
    ]


def _database_rows(providers: list[dict]) -> list[dict]:
    rows = {}
    for provider in providers:
        for model in provider.get("models", []):
            key = (provider_key(provider["name"]), model["id"])
            parameters = ModelParameters.model_validate(model.get("parameters") or {}).model_dump()
            rows[key] = {
                "provider_name": key[0],
                "model_id": key[1],
                "temperature": parameters["temperature"],
                "top_p": parameters["topP"],
                "max_tokens": parameters["maxTokens"],
                "reasoning_effort": parameters["reasoningEffort"],
                "updated_at": datetime.utcnow(),
            }
    return list(rows.values())


def save_model_parameters(providers: list[dict], write_settings: Callable[[], None]) -> None:
    rows = _database_rows(providers)
    with engine.begin() as connection:
        keys = [(row["provider_name"], row["model_id"]) for row in rows]
        connection.execute(delete(table).where(tuple_(table.c.provider_name, table.c.model_id).not_in(keys)))
        for row in rows:
            statement = insert(table).values(**row)
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c.provider_name, table.c.model_id],
                    set_={key: value for key, value in row.items() if key not in {"provider_name", "model_id"}},
                )
            )
        # A failed JSON write rolls back the database transaction as well.
        write_settings()


def migrate_model_parameters(connection) -> None:
    """Import JSON parameters once; existing database values remain authoritative."""
    path = get_user_settings_file()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        providers = enrich_providers(data.get("providers", []), {}, data.get("temperature", 0.5))
        for row in _database_rows(providers):
            connection.execute(insert(table).values(**row).on_conflict_do_nothing())
    except (ValueError, TypeError, KeyError) as error:
        logger.warning("迁移历史模型参数失败: %s", error)
