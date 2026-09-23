from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from sqlalchemy import DateTime, String, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_DATA_ROOT = Path(
    os.getenv(
        "CODESHIFT_DATA_DIR",
        str(_BACKEND_ROOT / ".codeshift"),
    )
)

_ANALYSES_DIR = _DATA_ROOT / "analyses"

_ANALYSES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "",
).strip()

_ANALYSES: dict[str, dict] = {}
_LOCK = Lock()


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    state: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


_ENGINE = None
_SESSION_LOCAL = None

if DATABASE_URL:
    _ENGINE = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

    _SESSION_LOCAL = sessionmaker(
        bind=_ENGINE,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(
        bind=_ENGINE
    )


def _analysis_file(
    analysis_id: str,
) -> Path:
    return (
        _ANALYSES_DIR
        / f"{analysis_id}.json"
    )


def _json_safe(
    value: object,
) -> object:
    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        Path,
    ):
        return str(value)

    if isinstance(
        value,
        os.PathLike,
    ):
        return os.fspath(value)

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            _json_safe(item)
            for item in value
        ]

    return None


def _write_analysis_disk(
    analysis_id: str,
    state: dict,
) -> None:
    path = _analysis_file(
        analysis_id
    )

    temp_path = path.with_suffix(
        ".json.tmp"
    )

    serialized_state = _json_safe(
        state
    )

    temp_path.write_text(
        json.dumps(
            serialized_state,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temp_path.replace(
        path
    )


def _read_analysis_disk(
    analysis_id: str,
) -> dict | None:
    path = _analysis_file(
        analysis_id
    )

    if not path.exists():
        return None

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    return (
        data
        if isinstance(data, dict)
        else None
    )


def _write_analysis_db(
    analysis_id: str,
    state: dict,
) -> None:
    if _SESSION_LOCAL is None:
        raise RuntimeError(
            "Database is not configured."
        )

    serialized_state = _json_safe(
        state
    )

    with _SESSION_LOCAL() as session:
        record = session.get(
            AnalysisRecord,
            analysis_id,
        )

        if record is None:
            record = AnalysisRecord(
                id=analysis_id,
                state=serialized_state,
            )
            session.add(record)
        else:
            record.state = serialized_state

        session.commit()


def _read_analysis_db(
    analysis_id: str,
) -> dict | None:
    if _SESSION_LOCAL is None:
        return None

    with _SESSION_LOCAL() as session:
        record = session.get(
            AnalysisRecord,
            analysis_id,
        )

        if record is None:
            return None

        state = record.state

        return (
            dict(state)
            if isinstance(state, dict)
            else None
        )


def _delete_analysis_db(
    analysis_id: str,
) -> bool:
    if _SESSION_LOCAL is None:
        return False

    with _SESSION_LOCAL() as session:
        record = session.get(
            AnalysisRecord,
            analysis_id,
        )

        if record is None:
            return False

        session.delete(record)
        session.commit()

        return True


def create_analysis(
    state: dict,
) -> str:
    analysis_id = str(
        uuid4()
    )

    with _LOCK:
        _ANALYSES[
            analysis_id
        ] = state

        if DATABASE_URL:
            _write_analysis_db(
                analysis_id,
                state,
            )
        else:
            _write_analysis_disk(
                analysis_id,
                state,
            )

    return analysis_id


def get_analysis(
    analysis_id: str,
) -> dict | None:
    with _LOCK:
        # PostgreSQL is the source of truth in AWS. Always refresh from
        # the database so polling requests on another ECS task do not
        # return stale cached state.
        if DATABASE_URL:
            state = _read_analysis_db(
                analysis_id
            )

            if state is None:
                return None

            _ANALYSES[
                analysis_id
            ] = state

            return state

        state = _ANALYSES.get(
            analysis_id
        )

        if state is not None:
            return state

        state = _read_analysis_disk(
            analysis_id
        )

        if state is None:
            return None

        _ANALYSES[
            analysis_id
        ] = state

        return state

def update_analysis(
    analysis_id: str,
    state: dict,
) -> None:
    with _LOCK:
        if DATABASE_URL:
            exists = (
                _read_analysis_db(
                    analysis_id
                )
                is not None
            )
        else:
            exists = (
                analysis_id
                in _ANALYSES
                or _analysis_file(
                    analysis_id
                ).exists()
            )

        if not exists:
            raise KeyError(
                "Analysis not found."
            )

        _ANALYSES[
            analysis_id
        ] = state

        if DATABASE_URL:
            _write_analysis_db(
                analysis_id,
                state,
            )
        else:
            _write_analysis_disk(
                analysis_id,
                state,
            )


def delete_analysis(
    analysis_id: str,
) -> bool:
    with _LOCK:
        existed = False

        if (
            analysis_id
            in _ANALYSES
        ):
            del _ANALYSES[
                analysis_id
            ]
            existed = True

        if DATABASE_URL:
            return (
                _delete_analysis_db(
                    analysis_id
                )
                or existed
            )

        path = _analysis_file(
            analysis_id
        )

        if path.exists():
            path.unlink()
            existed = True

        return existed
