from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_database: str
    openai_api_key: str
    openai_model: str = "gpt-5.4-mini"

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "Settings":
        required = ("MONGODB_URI", "MONGODB_DATABASE", "OPENAI_API_KEY")
        missing = [key for key in required if not str(values.get(key, "")).strip()]
        if missing:
            raise ConfigurationError(
                "Missing required Streamlit secrets: " + ", ".join(missing)
            )
        return cls(
            mongodb_uri=str(values["MONGODB_URI"]),
            mongodb_database=str(values["MONGODB_DATABASE"]),
            openai_api_key=str(values["OPENAI_API_KEY"]),
            openai_model=str(values.get("OPENAI_MODEL", "gpt-5.4-mini")),
        )
