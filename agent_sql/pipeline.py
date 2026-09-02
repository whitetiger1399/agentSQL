from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any, Protocol

from rapidfuzz import fuzz

from .database import MAX_RESULTS, DatabaseUnavailable
from .guardrails import obvious_rejection
from .llm import PlanExtractionError
from .models import AgentResult, Intent, ProcessingStep, QueryPlan, ResolvedFilters, SessionContext
from .resolution import ResolutionError, build_mongo_filter, merge_context, resolve_query_plan
from .typos import normalize_query_text


class Planner(Protocol):
    def extract_query_plan(self, message: str, context: SessionContext) -> QueryPlan: ...


class Repository(Protocol):
    def camera_documents(self) -> list[dict[str, Any]]: ...
    def find_traffic_frames(
        self,
        query_filter: dict[str, Any],
        limit: int = MAX_RESULTS,
        sort_descending: bool = False,
    ) -> list[dict[str, Any]]: ...


_LATEST_COUNT = re.compile(
    r"\b(?:latest|last)\s+(\d{1,3})\s+(?:frames?|records?|rows?)\b",
    re.IGNORECASE,
)
_FRESH_QUERY = re.compile(r"^\s*(?:show|find|get|list|give)\b", re.IGNORECASE)
_FOLLOW_UP = re.compile(
    r"^\s*(?:now|then|also|and|only|instead|what\s+about|how\s+about|same)\b",
    re.IGNORECASE,
)


def apply_result_controls(message: str, plan: QueryPlan) -> QueryPlan:
    """Apply safe, deterministic controls for an explicit latest-N phrase."""
    match = _LATEST_COUNT.search(message)
    if not match:
        return plan
    requested = min(int(match.group(1)), MAX_RESULTS)
    return plan.model_copy(update={"result_limit": max(1, requested), "sort_order": "latest"})


def _message_mentions_camera(message: str, cameras: list[dict[str, Any]]) -> bool:
    lowered = message.casefold()
    for camera in cameras:
        terms = [camera.get("camera_name", ""), camera.get("acronym", "")]
        terms.extend(camera.get("aliases", []))
        for raw_term in terms:
            term = str(raw_term).strip().casefold()
            if not term:
                continue
            if len(term) <= 4 and re.search(rf"\b{re.escape(term)}\b", lowered):
                return True
            if len(term) > 4 and fuzz.partial_ratio(term, lowered) >= 88:
                return True
    return False


def apply_context_policy(
    message: str, plan: QueryPlan, cameras: list[dict[str, Any]]
) -> QueryPlan:
    """Keep context for clear follow-ups, not fresh standalone requests."""
    if not _FRESH_QUERY.search(message) or _FOLLOW_UP.search(message):
        return plan
    updates: dict[str, Any] = {
        "inherit_cameras": False,
        "inherit_date": False,
        "inherit_time": False,
    }
    if not _message_mentions_camera(message, cameras):
        updates["camera_terms"] = []
    return plan.model_copy(update=updates)


def _filter_summary(
    filters: ResolvedFilters, result_limit: int, sort_order: str
) -> dict[str, Any]:
    return {
        "cameras": filters.camera_names or ["All cameras"],
        "date": (
            "No date filter (searching all available dates)"
            if filters.date_description == "Any date"
            else filters.date_description
        ),
        "selection": (
            f"Latest {result_limit} matching frame{'s' if result_limit != 1 else ''}"
            if sort_order == "latest"
            else "Chronological matching frames"
        ),
        "utc_intervals": [
            {"gte": start.isoformat(), "lt": end.isoformat()}
            for start, end in filters.intervals_utc
        ],
        "limit": result_limit,
        "sort": "captured_at descending" if sort_order == "latest" else "captured_at ascending",
    }


def _success_message(
    count: int,
    filters: ResolvedFilters,
    result_limit: int,
    sort_order: str,
) -> str:
    cameras = ", ".join(filters.camera_names) if filters.camera_names else "all cameras"
    if count == 0:
        return (
            f"No frames matched {cameras} for {filters.date_description.lower()} "
            "in Asia/Singapore time. Check the interpreted UTC bounds for the exact conversion."
        )
    if sort_order == "latest":
        if count == result_limit:
            return (
                f"Found the latest {count} available frame{'s' if count != 1 else ''} "
                f"for {cameras}."
            )
        return (
            f"Found {count} available frame{'s' if count != 1 else ''} for {cameras}; "
            f"fewer than the latest {result_limit} requested were available."
        )
    suffix = " The display is capped at 100 records." if count == MAX_RESULTS else ""
    return f"Found {count} frame{'s' if count != 1 else ''} for {cameras} ({filters.date_description}).{suffix}"


def _safe_value(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return value


def run_query(
    message: str,
    context: SessionContext,
    planner: Planner,
    repository: Repository,
    now: datetime | None = None,
) -> AgentResult:
    steps: list[ProcessingStep] = []
    normalization = normalize_query_text(message)
    normalized_message = normalization.text
    steps.append(
        ProcessingStep(
            name="1. Input normalization",
            status="completed",
            details={
                "normalized_text": normalized_message,
                "corrections": normalization.corrections or "None",
            },
        )
    )
    rejection = obvious_rejection(normalized_message)
    if rejection:
        steps.append(
            ProcessingStep(
                name="2. Pre-query safety checks",
                status="rejected",
                details={"decision": rejection},
            )
        )
        return AgentResult(
            status="rejected", message=rejection, context=context, processing_steps=steps
        )
    steps.append(
        ProcessingStep(
            name="2. Pre-query safety checks",
            status="passed",
            details={"scope": "Read-only traffic-camera request", "unsafe_patterns": "None"},
        )
    )

    try:
        plan = apply_result_controls(
            normalized_message,
            planner.extract_query_plan(normalized_message, context),
        )
        cameras = repository.camera_documents()
        plan = apply_context_policy(normalized_message, plan, cameras)
        steps.append(
            ProcessingStep(
                name="3. Structured value extraction",
                status="completed",
                details=_safe_value(plan.model_dump()),
            )
        )
        if plan.intent == Intent.REJECT:
            steps.append(
                ProcessingStep(
                    name="4. Model scope decision",
                    status="rejected",
                    details={"reason": plan.rejection_reason},
                )
            )
            return AgentResult(
                status="rejected",
                message=plan.rejection_reason or "That request is not supported.",
                context=context,
                processing_steps=steps,
            )
        merged_plan, _ = merge_context(plan, context)
        steps.append(
            ProcessingStep(
                name="4. Conversation context merge",
                status="completed",
                details=_safe_value(merged_plan.model_dump()),
            )
        )
        filters, updated_context = resolve_query_plan(merged_plan, cameras, now=now)
        steps.append(
            ProcessingStep(
                name="5. Camera and date resolution",
                status="completed",
                details=_safe_value(filters.model_dump()),
            )
        )
        mongo_filter = build_mongo_filter(filters)
        requested_limit = plan.result_limit or MAX_RESULTS
        steps.append(
            ProcessingStep(
                name="6. Safe PyMongo query construction",
                status="passed",
                details={
                    "collection": "traffic_frames",
                    "filter": _safe_value(mongo_filter),
                    "sort": {"captured_at": -1 if plan.sort_order == "latest" else 1},
                    "limit": requested_limit,
                    "operation": "find (read-only)",
                },
            )
        )
        records = repository.find_traffic_frames(
            mongo_filter,
            limit=requested_limit,
            sort_descending=plan.sort_order == "latest",
        )
        steps.append(
            ProcessingStep(
                name="7. Read-only execution",
                status="completed",
                details={"rows_returned": len(records), "hard_limit": MAX_RESULTS},
            )
        )
        return AgentResult(
            status="ok",
            message=_success_message(
                len(records), filters, requested_limit, plan.sort_order
            ),
            interpreted_filters=_filter_summary(filters, requested_limit, plan.sort_order),
            records=records,
            result_count=len(records),
            context=updated_context,
            processing_steps=steps,
        )
    except ResolutionError as exc:
        steps.append(
            ProcessingStep(
                name="Resolution",
                status="error",
                details={"message": str(exc), "suggestions": exc.suggestions},
            )
        )
        return AgentResult(
            status="clarification",
            message=str(exc),
            context=context,
            suggestions=exc.suggestions,
            processing_steps=steps,
        )
    except DatabaseUnavailable as exc:
        steps.append(ProcessingStep(name="Database execution", status="error", details={"message": str(exc)}))
        return AgentResult(status="error", message=str(exc), context=context, processing_steps=steps)
    except PlanExtractionError as exc:
        steps.append(ProcessingStep(name="Structured extraction", status="error", details={"message": str(exc)}))
        return AgentResult(status="error", message=str(exc), context=context, processing_steps=steps)
    except Exception:
        steps.append(
            ProcessingStep(
                name="Safe processing",
                status="error",
                details={"message": "The request could not be completed safely."},
            )
        )
        return AgentResult(
            status="error",
            message="I could not safely process that request. Please rephrase it and try again.",
            context=context,
            processing_steps=steps,
        )
