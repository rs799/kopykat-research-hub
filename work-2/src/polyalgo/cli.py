from __future__ import annotations

import argparse
import json
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from polyalgo.db import init_db, get_engine
from polyalgo.ingest.markets import fetch_and_store_markets
from polyalgo.ingest.orderbooks import snapshot_books
from polyalgo.ingest.wallets import ingest_wallet
from polyalgo.ingest.closed_positions import ingest_closed_positions
from polyalgo.ingest.tracked_wallets import add_wallet, remove_wallet, list_wallets
from polyalgo.ingest.activity import ingest_wallet_activity, ingest_tracked_wallets_activity
from polyalgo.scoring.clv import compute_and_store_wallet_clv
from polyalgo.scoring.wallets import score_all_wallets
from polyalgo.strategy.signals import generate_basic_wallet_signals, latest_candidate_signals
from polyalgo.strategy.paper import PaperBroker

console = Console()


def cmd_init_db(args):
    init_db()
    console.print("[green]Database initialized.[/green]")


def cmd_fetch_markets(args):
    count = fetch_and_store_markets(limit=args.limit)
    console.print(f"[green]Stored {count} markets.[/green]")


def cmd_snapshot_books(args):
    count = snapshot_books(limit=args.limit)
    console.print(f"[green]Stored {count} order-book snapshots.[/green]")


def cmd_ingest_wallet(args):
    result = ingest_wallet(args.wallet)
    console.print(
        f"[green]Ingested wallet {result['wallet']}: "
        f"{result['trades']} trades, {result['positions']} positions.[/green]"
    )


def cmd_ingest_closed_positions(args):
    result = ingest_closed_positions(args.wallet)
    if "error" in result:
        console.print(f"[red]Closed-position ingest failed for {result['wallet']}: {result['error']}[/red]")
        return
    console.print(
        f"[green]Ingested {result['closed_positions']} closed positions for {result['wallet']} "
        f"({result['missing_realized_pnl']} missing realized_pnl from the API).[/green]"
    )


def cmd_add_wallet(args):
    result = add_wallet(args.wallet, label=args.label, source=args.source, notes=args.notes)
    console.print(f"[green]Wallet {result['wallet']}: {result['status']}[/green]")


def cmd_remove_wallet(args):
    result = remove_wallet(args.wallet)
    if result["status"] == "not_found":
        console.print(f"[yellow]Wallet {result['wallet']} was not in the tracked list.[/yellow]")
    else:
        console.print(f"[green]Wallet {result['wallet']}: {result['status']}[/green]")


def cmd_list_wallets(args):
    wallets = list_wallets(active_only=not args.include_inactive)
    table = Table(title="Tracked Wallets")
    table.add_column("Wallet")
    table.add_column("Label")
    table.add_column("Source")
    table.add_column("Active")
    table.add_column("Last ingested")
    table.add_column("Score")
    table.add_column("Class")

    for w in wallets:
        table.add_row(
            w["wallet_address"][:14] + "...",
            w["label"] or "",
            w["source"] or "",
            "yes" if w["is_active"] else "no",
            w["last_ingested_at"] or "never",
            f"{w['final_score']:.1f}" if w["final_score"] is not None else "n/a",
            w["classification"] or "unscored",
        )
    console.print(table)


def cmd_ingest_wallet_activity(args):
    result = ingest_wallet_activity(args.wallet, limit=args.limit)
    if "error" in result:
        console.print(f"[red]Activity ingest failed for {result['wallet']}: {result['error']}[/red]")
        return
    console.print(
        f"[green]{result['wallet']}: fetched {result['fetched']}, inserted {result['inserted_raw']}, "
        f"skipped {result['skipped_duplicate']} duplicates, {result['parse_warnings']} parse warnings, "
        f"{result['lifecycle_events_created']} lifecycle events created.[/green]"
    )


def cmd_ingest_tracked_wallets_activity(args):
    results = ingest_tracked_wallets_activity()
    if not results:
        console.print("[yellow]No active tracked wallets. Use `add-wallet` first.[/yellow]")
        return
    for r in results:
        if "error" in r:
            console.print(f"[red]{r['wallet']}: {r['error']}[/red]")
        else:
            console.print(
                f"[green]{r['wallet']}[/green]: +{r['inserted_raw']} rows, "
                f"{r['lifecycle_events_created']} lifecycle events, {r['parse_warnings']} warnings"
            )


def cmd_show_wallet_activity(args):
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT event_type, condition_id, token_id, side, size, price,
                       usdc_size, timestamp, interpretation
                FROM wallet_lifecycle_events
                WHERE lower(wallet_address) = lower(:wallet)
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"wallet": args.wallet, "limit": args.limit},
        ).mappings().all()

    table = Table(title=f"Wallet activity: {args.wallet}")
    table.add_column("Time")
    table.add_column("Event")
    table.add_column("Token")
    table.add_column("Side")
    table.add_column("Size")
    table.add_column("Price")
    table.add_column("Interpretation")

    for r in rows:
        table.add_row(
            str(r["timestamp"]),
            r["event_type"],
            (r["token_id"] or "")[:10],
            r["side"] or "",
            f"{r['size']:.2f}" if r["size"] is not None else "",
            f"{r['price']:.3f}" if r["price"] is not None else "",
            r["interpretation"],
        )
    console.print(table)


def cmd_debug_wallet_activity(args):
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT activity_type, parsed_ok, parse_warning, raw_json
                FROM wallet_activity_raw
                WHERE lower(wallet_address) = lower(:wallet)
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"wallet": args.wallet, "limit": args.limit},
        ).mappings().all()

    for r in rows:
        console.print(f"[bold]{r['activity_type']}[/bold] parsed_ok={r['parsed_ok']} warning={r['parse_warning']}")
        if args.show_raw_keys:
            try:
                keys = sorted(json.loads(r["raw_json"]).keys())
                console.print(f"  raw keys: {keys}")
            except (TypeError, json.JSONDecodeError):
                console.print("  raw keys: <could not parse raw_json>")


def cmd_compute_clv(args):
    result = compute_and_store_wallet_clv(args.wallet, limit_trades=args.limit)
    console.print(
        f"[green]CLV computed for {result['computed']} trades[/green] "
        f"(skipped {result['skipped_ineligible_side']} non-BUY, "
        f"{result['skipped_bad_data']} missing/unusable data) for {result['wallet']}."
    )


def cmd_score_wallets(args):
    scores = score_all_wallets()
    table = Table(title="Wallet Scores (resolved-trade based)")
    table.add_column("Wallet")
    table.add_column("Resolved trades")
    table.add_column("Realized PnL")
    table.add_column("Realized ROI")
    table.add_column("CLV score")
    table.add_column("Score")
    table.add_column("Class")

    for s in sorted(scores, key=lambda x: x.final_score, reverse=True)[:20]:
        roi_str = f"{s.realized_roi:.3f}" if s.realized_roi is not None else "n/a"
        table.add_row(
            s.wallet[:12] + "...",
            str(s.resolved_trade_count),
            f"${s.realized_pnl:.2f}",
            roi_str,
            f"{s.clv_score:.2f}",
            f"{s.final_score:.1f}",
            s.classification,
        )

    console.print(table)
    console.print(
        "[dim]Score is 0-100 based on resolved-market performance only. "
        "Unrealized/open-position PnL is intentionally excluded. "
        "See the dashboard for the full component breakdown behind each score.[/dim]"
    )


def cmd_generate_signals(args):
    count = generate_basic_wallet_signals(default_size_usd=args.size)
    console.print(f"[green]Generated {count} placeholder signals.[/green]")


def cmd_paper_execute(args):
    broker = PaperBroker(bankroll=args.bankroll)
    count = broker.execute_latest(limit=args.limit)
    console.print(f"[green]Paper-filled {count} orders.[/green]")


def cmd_show_signals(args):
    signals = latest_candidate_signals(limit=args.limit)
    table = Table(title="Latest Candidate Signals")
    for col in ["Market", "Token", "Entry", "Fair", "Net edge", "Reason"]:
        table.add_column(col)

    for s in signals:
        table.add_row(
            s.market_id[:10],
            s.token_id[:10],
            f"{s.entry_price:.3f}",
            f"{s.fair_probability:.3f}",
            f"{s.net_edge:.3f}",
            s.reason,
        )
    console.print(table)


def build_parser():
    parser = argparse.ArgumentParser(description="Polymarket algo framework CLI")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("init-db")
    p.set_defaults(func=cmd_init_db)

    p = sub.add_parser("fetch-markets")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=cmd_fetch_markets)

    p = sub.add_parser("snapshot-books")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_snapshot_books)

    p = sub.add_parser("ingest-wallet")
    p.add_argument("--wallet", required=True)
    p.set_defaults(func=cmd_ingest_wallet)

    p = sub.add_parser("ingest-closed-positions")
    p.add_argument("--wallet", required=True)
    p.set_defaults(func=cmd_ingest_closed_positions)

    p = sub.add_parser("add-wallet")
    p.add_argument("--wallet", required=True)
    p.add_argument("--label", default=None)
    p.add_argument("--source", default="manual")
    p.add_argument("--notes", default=None)
    p.set_defaults(func=cmd_add_wallet)

    p = sub.add_parser("remove-wallet")
    p.add_argument("--wallet", required=True)
    p.set_defaults(func=cmd_remove_wallet)

    p = sub.add_parser("list-wallets")
    p.add_argument("--include-inactive", action="store_true")
    p.set_defaults(func=cmd_list_wallets)

    p = sub.add_parser("ingest-wallet-activity")
    p.add_argument("--wallet", required=True)
    p.add_argument("--limit", type=int, default=500)
    p.set_defaults(func=cmd_ingest_wallet_activity)

    p = sub.add_parser("ingest-tracked-wallets-activity")
    p.set_defaults(func=cmd_ingest_tracked_wallets_activity)

    p = sub.add_parser("show-wallet-activity")
    p.add_argument("--wallet", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_show_wallet_activity)

    p = sub.add_parser("debug-wallet-activity")
    p.add_argument("--wallet", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--show-raw-keys", action="store_true")
    p.set_defaults(func=cmd_debug_wallet_activity)

    p = sub.add_parser("compute-clv")
    p.add_argument("--wallet", required=True)
    p.add_argument("--limit", type=int, default=300)
    p.set_defaults(func=cmd_compute_clv)

    p = sub.add_parser("score-wallets")
    p.set_defaults(func=cmd_score_wallets)

    p = sub.add_parser("generate-signals")
    p.add_argument("--size", type=float, default=25.0)
    p.set_defaults(func=cmd_generate_signals)

    p = sub.add_parser("show-signals")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_show_signals)

    p = sub.add_parser("paper-execute")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--bankroll", type=float, default=1000.0)
    p.set_defaults(func=cmd_paper_execute)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

