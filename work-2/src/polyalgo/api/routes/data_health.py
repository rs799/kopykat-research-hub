from __future__ import annotations

"""
Real data-health metrics computed from the DB, replacing KopyKat's
fabricated mock numbers. Severity, rawField, and parsedField on each warning
are placeholders (see TODO below) - we don't currently classify parse
failures at that granularity, only whether a row parsed cleanly and why.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.schemas import DataHealth, DataHealthEndpoint, Warning

router = APIRouter()

# Tables whose "freshness" we can report on. Each maps to the timestamp
# column used to compute lastIngestion.
_TRACKED_TABLES = {
    "wallet_trades": "ts",
    "wallet_closed_positions": "ingested_at",
    "wallet_activity_raw": "created_at",
    "orderbook_snapshots": "ts",
    "markets": "updated_at",
}


@router.get("/api/data-health", response_model=DataHealth)
def get_data_health(engine: Engine = Depends(get_engine_dependency)) -> DataHealth:
    endpoints: list[DataHealthEndpoint] = []
    total_rows = 0

    with engine.begin() as conn:
        for table, ts_col in _TRACKED_TABLES.items():
            row = conn.execute(
                text(f"SELECT COUNT(*) AS n, MAX({ts_col}) AS last_ts FROM {table}")
            ).mappings().first()
            n = int(row["n"] or 0)
            total_rows += n
            endpoints.append(
                DataHealthEndpoint(
                    name=table,
                    status="ok" if n > 0 else "no_data",
                    lastIngestion=str(row["last_ts"]) if row["last_ts"] else None,
                )
            )

        lifecycle_events = conn.execute(
            text("SELECT COUNT(*) AS n FROM wallet_lifecycle_events")
        ).mappings().first()["n"]

        warning_rows = conn.execute(
            text("""
                SELECT wallet_address, activity_type, created_at, parse_warning
                FROM wallet_activity_raw
                WHERE parsed_ok = 0
                ORDER BY created_at DESC
                LIMIT 200
            """)
        ).mappings().all()

    warnings = [
        Warning(
            timestamp=str(r["created_at"]) if r["created_at"] else None,
            endpoint="wallet_activity",
            wallet=r["wallet_address"],
            # TODO: no severity classification exists yet - every parse
            # warning is reported as "low" until one is built. Do not infer
            # severity from the warning text without an explicit rule.
            severity="low",
            warning=r["activity_type"] or "unknown_type",
            rawField=None,
            parsedField=None,
            message=r["parse_warning"] or "",
        )
        for r in warning_rows
    ]

    return DataHealth(
        endpoints=endpoints,
        rawRows=total_rows,
        lifecycleEvents=int(lifecycle_events or 0),
        unresolvedIssues=len(warnings),
        warnings=warnings,
    )
