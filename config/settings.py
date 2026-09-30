from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    # Gemini
    model: str = "gemini-3.5-flash-lite"
    max_retries: int = 3
    timeout: int = 120
    backoff_base: float = 2.0

    # Translation
    max_chunk_tokens: int = 1200

    # Runtime
    progress_dir: str = "progress"
    cache_dir: str = "cache"
    output_format: str = "epub"

    # Research
    research_enabled: bool = True

    # QA
    qa_enabled: bool = True
    qa_max_retries: int = 2

    @property
    def gemini_api_key(self) -> str:
        key = os.environ.get("GEMINI_API_KEY")

        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY belum tersedia di environment."
            )

        return key

    def validate(self) -> None:
        if not self.model.strip():
            raise ValueError(
                "model tidak boleh kosong."
            )

        if self.max_retries < 0:
            raise ValueError(
                "max_retries tidak boleh negatif."
            )

        if self.timeout <= 0:
            raise ValueError(
                "timeout harus lebih besar dari 0."
            )

        if self.backoff_base <= 0:
            raise ValueError(
                "backoff_base harus lebih besar dari 0."
            )

        if self.max_chunk_tokens <= 0:
            raise ValueError(
                "max_chunk_tokens harus lebih besar dari 0."
            )

        if self.output_format.lower() not in {
            "epub",
            "docx",
        }:
            raise ValueError(
                "output_format harus 'epub' atau 'docx'."
            )

        if self.qa_max_retries < 0:
            raise ValueError(
                "qa_max_retries tidak boleh negatif."
            )

        if not self.progress_dir.strip():
            raise ValueError(
                "progress_dir tidak boleh kosong."
            )

        if not self.cache_dir.strip():
            raise ValueError(
                "cache_dir tidak boleh kosong."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_CONFIG_FIELDS = {
    "model": str,
    "max_retries": int,
    "timeout": int,
    "backoff_base": float,
    "max_chunk_tokens": int,
    "progress_dir": str,
    "cache_dir": str,
    "output_format": str,
    "research_enabled": bool,
    "qa_enabled": bool,
    "qa_max_retries": int,
}


def _convert_value(
    field_name: str,
    value: Any,
) -> Any:
    expected_type = _CONFIG_FIELDS[field_name]

    if expected_type is bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {
                "1",
                "true",
                "yes",
                "on",
            }:
                return True

            if normalized in {
                "0",
                "false",
                "no",
                "off",
            }:
                return False

        raise ValueError(
            f"Nilai {field_name!r} harus boolean."
        )

    try:
        return expected_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Nilai {field_name!r} tidak valid: {value!r}"
        ) from exc


def _apply_values(
    config: AppConfig,
    values: dict[str, Any],
) -> AppConfig:
    data = config.to_dict()

    for field_name, value in values.items():
        if field_name not in _CONFIG_FIELDS:
            raise ValueError(
                f"Field konfigurasi tidak dikenal: "
                f"{field_name}"
            )

        data[field_name] = _convert_value(
            field_name,
            value,
        )

    result = AppConfig(**data)
    result.validate()

    return result


def _load_config_file(
    project_dir: Path | None,
) -> dict[str, Any]:
    if project_dir is None:
        return {}

    config_path = project_dir / "config.json"

    if not config_path.exists():
        return {}

    if not config_path.is_file():
        raise ValueError(
            f"config.json bukan file: {config_path}"
        )

    try:
        with config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"config.json tidak valid: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "config.json harus berupa JSON object."
        )

    return data


def _load_environment() -> dict[str, Any]:
    values: dict[str, Any] = {}

    for field_name in _CONFIG_FIELDS:
        env_name = f"WN_{field_name.upper()}"

        if env_name in os.environ:
            values[field_name] = os.environ[env_name]

    return values


def load_config(
    project_dir: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> AppConfig:
    """
    Load configuration with precedence:

        default
            ↓
        config.json
            ↓
        WN_* environment variables
            ↓
        runtime overrides

    GEMINI_API_KEY tetap hanya berasal dari environment
    dan tidak pernah disimpan ke config.json.
    """

    project_path = (
        Path(project_dir)
        if project_dir is not None
        else None
    )

    config = AppConfig()

    file_values = _load_config_file(
        project_path
    )

    if file_values:
        config = _apply_values(
            config,
            file_values,
        )

    environment_values = _load_environment()

    if environment_values:
        config = _apply_values(
            config,
            environment_values,
        )

    if overrides:
        config = _apply_values(
            config,
            overrides,
        )

    config.validate()

    return config
