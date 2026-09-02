from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

import certifi
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError


ALLOWED_COLLECTIONS = ("cameras", "traffic_frames")
MAX_RESULTS = 100
_ALLOWED_FILTER_FIELDS = {"camera_name", "captured_at"}
_ALLOWED_OPERATORS = {"$and", "$or", "$in", "$gte", "$lt"}


class DatabaseUnavailable(RuntimeError):
    pass


class UnsafeQuery(ValueError):
    pass


def _validate_filter(value: Any, parent_key: str | None = None) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key.startswith("$"):
                if key not in _ALLOWED_OPERATORS:
                    raise UnsafeQuery(f"MongoDB operator {key!r} is not allowed")
            elif key not in _ALLOWED_FILTER_FIELDS:
                raise UnsafeQuery(f"MongoDB field {key!r} is not allowed")
            _validate_filter(nested, key)
    elif isinstance(value, list):
        for nested in value:
            _validate_filter(nested, parent_key)
    elif parent_key in {"$and", "$or"}:
        raise UnsafeQuery(f"Operator {parent_key} must contain filter documents")


def display_safe(document: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in document.items():
        if isinstance(value, ObjectId):
            safe[key] = str(value)
        elif isinstance(value, datetime):
            aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            safe[key] = aware.astimezone(timezone.utc).isoformat()
        elif isinstance(value, list):
            safe[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
        else:
            safe[key] = value
    return safe


class MongoRepository:
    def __init__(self, uri: str, database: str, timeout_ms: int = 5_000):
        try:
            self._client = MongoClient(
                uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                socketTimeoutMS=timeout_ms,
                tlsCAFile=certifi.where(),
            )
        except PyMongoError as exc:
            raise DatabaseUnavailable("MongoDB is currently unavailable.") from exc
        self._database = self._client[database]

    def ping(self) -> bool:
        try:
            return bool(self._client.admin.command("ping").get("ok"))
        except PyMongoError as exc:
            raise DatabaseUnavailable("MongoDB is currently unavailable.") from exc

    def list_allowed_collections(self) -> list[str]:
        return list(ALLOWED_COLLECTIONS)

    def preview_collection(self, name: str, limit: int = MAX_RESULTS) -> list[dict[str, Any]]:
        if name not in ALLOWED_COLLECTIONS:
            raise UnsafeQuery("That collection is not available for preview.")
        safe_limit = max(1, min(int(limit), MAX_RESULTS))
        sort = [("captured_at", ASCENDING)] if name == "traffic_frames" else [("camera_id", ASCENDING)]
        try:
            cursor = self._database[name].find({}, limit=safe_limit).sort(sort)
            return [display_safe(document) for document in cursor]
        except PyMongoError as exc:
            raise DatabaseUnavailable("The collection preview could not be loaded.") from exc

    def camera_documents(self) -> list[dict[str, Any]]:
        try:
            cursor = self._database["cameras"].find(
                {}, {"_id": 0, "camera_name": 1, "acronym": 1, "aliases": 1, "active": 1}
            ).limit(MAX_RESULTS)
            return list(cursor)
        except PyMongoError as exc:
            raise DatabaseUnavailable("Camera metadata could not be loaded.") from exc

    def find_traffic_frames(
        self,
        query_filter: Mapping[str, Any],
        limit: int = MAX_RESULTS,
        sort_descending: bool = False,
    ) -> list[dict[str, Any]]:
        _validate_filter(query_filter)
        safe_limit = max(1, min(int(limit), MAX_RESULTS))
        try:
            cursor = (
                self._database["traffic_frames"]
                .find(dict(query_filter), limit=safe_limit)
                .sort("captured_at", DESCENDING if sort_descending else ASCENDING)
            )
            return [display_safe(document) for document in cursor]
        except PyMongoError as exc:
            raise DatabaseUnavailable("Traffic frames could not be loaded.") from exc
