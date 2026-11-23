"""Remove seeded demo data while keeping one account.

Dry run is the default: it reads the database and prints how many rows would
be removed from each table. Pass ``--execute`` to delete, then type the
confirmation phrase when asked.

What is removed:
  * users whose email ends with ``@dotkonnekt.example`` (the demo accounts),
    except the account passed as ``--keep-user-id``;
  * every row that references those accounts, directly or through other rows
    (ideas they wrote, groups, ideathons, delivery, recognition, and so on).

Rows that only reference the kept account are left alone. Shared lookup
tables (categories, badges, platform_settings) are not touched. Teams are
kept too, but any reference to a removed account (for example a team's lead)
is cleared to NULL.

The foreign keys are read from the live schema, so tables added later are
handled without editing this file.

Usage (from backend/):

    uv run python -m app.seed.purge --database-url "<hosted url>" --keep-user-id <uuid>            # dry run
    uv run python -m app.seed.purge --database-url "<hosted url>" --keep-user-id <uuid> --execute  # delete

The URL must use the asyncpg driver and SSL, for example
postgresql+asyncpg://user:pass@host:5432/db?ssl=require. Local hosts are refused.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import ForeignKeyConstraint, MetaData, Table, delete, or_, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

SEED_EMAIL_SUFFIX = "@dotkonnekt.example"
CONFIRM_PHRASE = "DELETE SEED DATA"
USERS_TABLE = "users"
# Shared tables that survive. References from them to removed accounts are set to NULL.
DETACH_TABLES = frozenset({"teams"})
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})
CHUNK = 500

Row = tuple[Any, ...]

logger = logging.getLogger("purge")


@dataclass
class Detach:
    """Set one nullable foreign key column to NULL where it points at a removed row."""

    table: Table
    column: str
    values: list[Any]


@dataclass
class Plan:
    """What to change, per table, in the order the changes must run."""

    tables: dict[str, Table]
    keys: dict[str, list[str]]
    rows: dict[str, set[Row]]
    order: list[str]
    detach: list[Detach]


def _key_columns(table: Table) -> list[str]:
    """Columns that identify a row: the primary key, or every column if there is none."""
    pk = [c.name for c in table.primary_key.columns]
    return pk or [c.name for c in table.columns]


def _in_clause(table: Table, names: Sequence[str], values: list[Row]) -> Any:
    """Build ``(cols) IN (values)`` for one or several columns."""
    cols = [table.c[n] for n in names]
    if len(cols) == 1:
        return cols[0].in_([v[0] for v in values])
    return tuple_(*cols).in_(values)


def _incoming(md: MetaData) -> dict[str, list[tuple[Table, ForeignKeyConstraint]]]:
    """Map each referenced table name to the (child table, foreign key) pairs that point at it."""
    out: dict[str, list[tuple[Table, ForeignKeyConstraint]]] = defaultdict(list)
    for table in md.tables.values():
        for fk in table.foreign_key_constraints:
            out[fk.referred_table.name].append((table, fk))
    return out


async def build_plan(conn: AsyncConnection, keep_id: uuid.UUID) -> Plan:
    """Find every row that must go, following foreign keys from the seed accounts.

    Args:
        conn: Open connection. Only reads are issued here.
        keep_id: The account that must survive. It is never selected as a root.

    Returns:
        The plan, including the delete order (referencing tables before referenced ones).

    Raises:
        RuntimeError: If foreign keys between the affected tables form a cycle.
    """
    started = time.monotonic()
    logger.info("Reading the schema...")
    md = MetaData()
    await conn.run_sync(md.reflect)
    incoming = _incoming(md)
    logger.info(
        "Schema read: %d tables, %d foreign keys (%.1fs)",
        len(md.tables),
        sum(len(t.foreign_key_constraints) for t in md.tables.values()),
        time.monotonic() - started,
    )

    keys = {name: _key_columns(table) for name, table in md.tables.items()}

    # Columns to read for each table: its identifying columns plus any column another table references.
    needed: dict[str, list[str]] = {}
    for name in md.tables:
        cols = set(keys[name])
        for _child, fk in incoming.get(name, []):
            cols.update(e.column.name for e in fk.elements)
        needed[name] = sorted(cols)

    users = md.tables[USERS_TABLE]
    root_stmt = select(*[users.c[n] for n in needed[USERS_TABLE]]).where(
        users.c.email.ilike(f"%{SEED_EMAIL_SUFFIX}"),
        users.c.id != keep_id,
    )
    rows: dict[str, set[Row]] = defaultdict(set)
    detach: list[Detach] = []
    pending: deque[tuple[str, set[Row]]] = deque()
    pending.append((USERS_TABLE, {tuple(r) for r in (await conn.execute(root_stmt)).all()}))

    while pending:
        name, batch = pending.popleft()
        fresh = batch - rows[name]
        if not fresh:
            continue
        rows[name] |= fresh
        logger.info(
            "Found %d row(s) in %s (%d total so far, %d queued)",
            len(fresh),
            name,
            sum(len(r) for r in rows.values()),
            len(pending),
        )
        index = {col: i for i, col in enumerate(needed[name])}
        for child, fk in incoming.get(name, []):
            child_cols = [e.parent.name for e in fk.elements]
            parent_idx = [index[e.column.name] for e in fk.elements]
            values = list({tuple(r[i] for i in parent_idx) for r in fresh})
            values = [v for v in values if all(x is not None for x in v)]
            if child.name in DETACH_TABLES:
                # Keep the shared row; only clear the reference(s) to the removed rows.
                for column in child_cols:
                    if not child.c[column].nullable:
                        raise RuntimeError(
                            f"{child.name}.{column} points at removed rows but is NOT NULL"
                        )
                    detach.append(
                        Detach(
                            table=child,
                            column=column,
                            values=[v[child_cols.index(column)] for v in values],
                        )
                    )
                continue
            child_needed = needed[child.name]
            for start in range(0, len(values), CHUNK):
                chunk = values[start : start + CHUNK]
                stmt = select(*[child.c[n] for n in child_needed]).where(
                    _in_clause(child, child_cols, chunk)
                )
                found = {tuple(r) for r in (await conn.execute(stmt)).all()}
                pending.append((child.name, found))

    logger.info("Planning done in %.1fs; sorting delete order", time.monotonic() - started)
    order = _delete_order(md, {name for name, found in rows.items() if found})
    return Plan(
        tables={name: md.tables[name] for name in rows if rows[name]},
        keys=keys,
        rows={name: rows[name] for name in rows if rows[name]},
        order=order,
        detach=detach,
    )


def _delete_order(md: MetaData, affected: set[str]) -> list[str]:
    """Topologically sort affected tables so each table is deleted before the tables it references.

    Self-references are handled inside one DELETE statement, so they are ignored here.
    """
    must_precede: dict[str, set[str]] = {name: set() for name in affected}
    for name in affected:
        for fk in md.tables[name].foreign_key_constraints:
            parent = fk.referred_table.name
            if parent in affected and parent != name:
                must_precede[name].add(parent)

    order: list[str] = []
    # How many tables still have to be deleted before each name.
    pointed_at: dict[str, int] = defaultdict(int)
    for deps in must_precede.values():
        for dep in deps:
            pointed_at[dep] += 1
    ready = deque(sorted(name for name in affected if pointed_at[name] == 0))
    while ready:
        name = ready.popleft()
        order.append(name)
        for dep in sorted(must_precede[name]):
            pointed_at[dep] -= 1
            if pointed_at[dep] == 0:
                ready.append(dep)
    if len(order) != len(affected):
        stuck = sorted(affected - set(order))
        raise RuntimeError(f"Foreign keys form a cycle between tables: {', '.join(stuck)}")
    return order


async def apply_plan(conn: AsyncConnection, plan: Plan) -> dict[str, int]:
    """Delete the planned rows, children first, inside the caller's transaction.

    Args:
        conn: Connection with an open transaction.
        plan: Output of :func:`build_plan`.

    Returns:
        Number of rows deleted per table.
    """
    for item in plan.detach:
        if item.values:
            logger.info("Clearing %s.%s on %d row(s)", item.table.name, item.column, len(set(item.values)))
            await conn.execute(
                update(item.table)
                .where(item.table.c[item.column].in_(sorted(set(item.values), key=repr)))
                .values({item.column: None})
            )
    deleted: dict[str, int] = {}
    for name in plan.order:
        table = plan.tables[name]
        keys = plan.keys[name]
        values = sorted(plan.rows[name], key=repr)
        logger.info("Deleting %d row(s) from %s", len(values), name)
        count = 0
        for start in range(0, len(values), CHUNK):
            chunk = values[start : start + CHUNK]
            result = await conn.execute(delete(table).where(_in_clause(table, keys, chunk)))
            count += result.rowcount or 0
        deleted[name] = count
        logger.info("Deleted %d from %s", count, name)
    return deleted


async def kept_references(conn: AsyncConnection, plan: Plan, keep_id: uuid.UUID) -> dict[str, int]:
    """Count rows slated for deletion that also reference the kept account.

    Such rows belong to the kept account's content (for example a comment it
    wrote on a seed idea) but would be removed because they point at seed data.
    They need a human decision before --execute.
    """
    found: dict[str, int] = {}
    for name in plan.order:
        table = plan.tables[name]
        uuid_cols = [c for c in table.columns if isinstance(c.type, PgUUID)]
        if not uuid_cols:
            continue
        keys = plan.keys[name]
        stmt = select(*[table.c[k] for k in keys]).where(
            or_(*[c == keep_id for c in uuid_cols])
        )
        touching = {tuple(r) for r in (await conn.execute(stmt)).all()}
        count = len(touching & plan.rows[name])
        if count:
            found[name] = count
    return found


def _print_report(plan: Plan, touching: dict[str, int]) -> None:
    print("Rows that would be deleted (in this order):")
    for name in plan.order:
        print(f"  {len(plan.rows[name]):>7}  {name}")
    print("References cleared to NULL (rows are kept):")
    for item in plan.detach:
        print(f"  {len(set(item.values)):>7}  {item.table.name}.{item.column}")
    users = plan.rows.get(USERS_TABLE, set())
    print(f"\nSeed accounts to delete: {len(users)}")
    if touching:
        print("\nREVIEW: these rows will be deleted but also reference the kept account:")
        for name, count in touching.items():
            print(f"  {count:>7}  {name}")
    else:
        print("\nNo rows to be deleted reference the kept account.")


async def _kept_account(conn: AsyncConnection, keep_id: uuid.UUID) -> tuple[str, str] | None:
    result = await conn.execute(
        text("select email, name from users where id = :id"), {"id": keep_id}
    )
    row = result.first()
    return (str(row[0]), str(row[1])) if row else None


async def _run(url: str, keep_id: uuid.UUID, execute: bool) -> int:
    parsed = make_url(url)
    print(f"Database: {parsed.host}:{parsed.port or 5432}/{parsed.database}")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            kept = await _kept_account(conn, keep_id)
            if kept is None:
                print(f"No user with id {keep_id}. Nothing was changed.")
                return 1
            print(f"Keeping: {kept[1]} <{kept[0]}>")
            plan = await build_plan(conn, keep_id)
            touching = await kept_references(conn, plan, keep_id)
        _print_report(plan, touching)

        if not execute:
            print("\nDry run only. Re-run with --execute to delete.")
            return 0

        if not sys.stdin.isatty():
            print("--execute needs an interactive terminal so the confirmation can be typed.")
            return 1
        answer = input(f"\nType {CONFIRM_PHRASE!r} to delete these rows: ")
        if answer.strip() != CONFIRM_PHRASE:
            print("Confirmation did not match. Nothing was changed.")
            return 1

        # Rebuild the plan inside the transaction, so the delete matches the current data.
        # Everything below runs in one transaction: Ctrl-C or an error rolls it all back.
        logger.info("Starting delete in one transaction (Ctrl-C rolls back)")
        async with engine.begin() as conn:
            fresh = await build_plan(conn, keep_id)
            deleted = await apply_plan(conn, fresh)
        logger.info("Transaction committed")
        print("\nDeleted:")
        for name in fresh.order:
            print(f"  {deleted.get(name, 0):>7}  {name}")
        print(f"Cleared {len(fresh.detach)} reference column(s) to NULL.")
        print("\nDone. The kept account was not touched.")
        return 0
    finally:
        await engine.dispose()


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep-user-id", type=uuid.UUID, required=True, help="Account to keep.")
    parser.add_argument("--execute", action="store_true", help="Delete the rows (default is a dry run).")
    parser.add_argument(
        "--database-url",
        required=True,
        help="Async SQLAlchemy URL of the HOSTED database. Required; there is no default.",
    )
    args = parser.parse_args()
    host = make_url(args.database_url).host or ""
    if host in LOCAL_HOSTS:
        print(f"Refusing to run against a local database ({host}). This script is for the hosted database only.")
        sys.exit(2)
    sys.exit(asyncio.run(_run(args.database_url, args.keep_user_id, args.execute)))


if __name__ == "__main__":
    main()
