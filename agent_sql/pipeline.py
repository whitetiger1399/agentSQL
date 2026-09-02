from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Protocol

from .database import MAX_RESULTS, DatabaseUnavailable
from .guardrails import obvious_rejection
from .llm import PlanExtractionError
from .models import AgentResult, Intent, QueryPlan, ResolvedFilters, SessionContext
from .resolution import ResolutionError, build_mongo_filter, merge_context, resolve_query_plan


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
    r"\b(?:latest|lastest|last)\s+(\d{1,3})\s+(?:frames?|records?|rows?)\b",
    re.IGNORECASE,
)


def apply_result_controls(message: str, plan: QueryPlan) -> QueryPlan:
    """Apply safe, deterministic controls for an explicit latest-N phrase."""
    match = _LATEST_COUNT.search(message)
    if not match:
        return plan
    requested = min(int(match.group(1)), MAX_RESULTS)
    return plan.model_copy(update={"result_limit": max(1, requested), "sort_order": "latest"})


def _filter_summary(
    filters: ResolvedFilters, result_limit: int, sort_order: str
) -> dict[str, Any]:
    return {
        "cameras": filters.camera_names or ["All cameras"],
        "date": filters.date_description,
        "utc_intervals": [
            {"gte": start.isoformat(), "lt": end.isoformat()}
            for start, end in filters.intervals_utc
        ],
        "limit": result_limit,
        "sort": "captured_at descending" if sort_order == "latest" else "captured_at ascending",
    }


def _success_message(count: int, filters: ResolvedFilters) -> str:
    cameras = ", ".join(filters.camera_names) if filters.camera_names else "all cameras"
    if count == 0:
        return f"No frames matched {cameras} for {filters.date_description.lower()}."
    suffix = " The display is capped at 100 records." if count == MAX_RESULTS else ""
    return f"Found {count} frame{'s' if count != 1 else ''} for {cameras} ({filters.date_description}).{suffix}"


def run_query(
    message: str,
    context: SessionContext,
    planner: Planner,
    repository: Repository,
    now: datetime | None = None,
) -> AgentResult:
    rejection = obvious_rejection(message)
    if rejection:
        return AgentResult(status="rejected", message=rejection, context=context)

    try:
        plan = apply_result_controls(message, planner.extract_query_plan(message, context))
        if plan.intent == Intent.REJECT:
            return AgentResult(
                status="rejected",
                message=plan.rejection_reason or "That request is not supported.",
                context=context,
            )
        merged_plan, _ = merge_context(plan, context)
        cameras = repository.camera_documents()
        filters, updated_context = resolve_query_plan(merged_plan, cameras, now=now)
        mongo_filter = build_mongo_filter(filters)
        requested_limit = plan.result_limit or MAX_RESULTS
        records = repository.find_traffic_frames(
            mongo_filter,
            limit=requested_limit,
            sort_descending=plan.sort_order == "latest",
        )
        return AgentResult(
            status="ok",
            message=_success_message(len(records), filters),
            interpreted_filters=_filter_summary(filters, requested_limit, plan.sort_order),
            records=records,
            result_count=len(records),
            context=updated_context,
        )
    except ResolutionError as exc:
        return AgentResult(
            status="clarification",
            message=str(exc),
            context=context,
            suggestions=exc.suggestions,
        )
    except DatabaseUnavailable as exc:
        return AgentResult(status="error", message=str(exc), context=context)
    except PlanExtractionError as exc:
        return AgentResult(status="error", message=str(exc), context=context)
    except Exception:
        return AgentResult(
            status="error",
            message="I could not safely process that request. Please rephrase it and try again.",
            context=context,
        )
