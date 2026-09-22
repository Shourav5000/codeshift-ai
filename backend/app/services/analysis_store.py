from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4


_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_DATA_ROOT = Path(
    os.getenv(
        "CODESHIFT_DATA_DIR",
        str(_BACKEND_ROOT / ".codeshift"),
    )
)

_ANALYSES_DIR = (
    _DATA_ROOT
    / "analyses"
)

_ANALYSES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


_ANALYSES: dict[str, dict] = {}

_LOCK = Lock()


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
    """
    Convert workflow state into a JSON-persistable representation.

    Runtime filesystem objects such as pathlib.Path are persisted as
    strings. Ordinary nested dictionaries/lists are preserved.

    Unknown runtime-only objects are represented as null rather than
    preventing the entire analysis from being persisted.
    """

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
        return str(
            value
        )

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _json_safe(
                item
            )
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
            _json_safe(
                item
            )
            for item in value
        ]

    if isinstance(
        value,
        os.PathLike,
    ):
        return os.fspath(
            value
        )

    return None


def _write_analysis(
    analysis_id: str,
    state: dict,
) -> None:
    """
    Atomically persist an analysis state to disk.
    """

    path = _analysis_file(
        analysis_id
    )

    temp_path = path.with_suffix(
        ".json.tmp"
    )

    serialized_state = (
        _json_safe(
            state
        )
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


def _read_analysis(
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

    if not isinstance(
        data,
        dict,
    ):
        return None

    return data


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

        _write_analysis(
            analysis_id,
            state,
        )

    return analysis_id


def get_analysis(
    analysis_id: str,
) -> dict | None:

    with _LOCK:

        state = _ANALYSES.get(
            analysis_id
        )

        if state is not None:
            return state

        state = _read_analysis(
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

        exists_in_memory = (
            analysis_id
            in _ANALYSES
        )

        exists_on_disk = (
            _analysis_file(
                analysis_id
            ).exists()
        )

        if (
            not exists_in_memory
            and not exists_on_disk
        ):
            raise KeyError(
                "Analysis not found."
            )

        _ANALYSES[
            analysis_id
        ] = state

        _write_analysis(
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

        path = _analysis_file(
            analysis_id
        )

        if path.exists():

            path.unlink()

            existed = True

        return existed