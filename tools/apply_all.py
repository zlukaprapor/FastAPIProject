#!/usr/bin/env python3
import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List, Tuple

import psycopg2
from psycopg2.extensions import connection as PgConnection


@dataclass
class DbHandle:
    shard_key: str
    dsn: str
    conn: PgConnection
    gid: str
    prepared: bool = False


def load_mapping(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("mapping file must be a non-empty JSON object: {shard_key: dsn}")
    return mapping


def read_sql(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        sql_text = f.read()
    if not sql_text.strip():
        raise ValueError("SQL file is empty")
    return sql_text


def connect_all(mapping: Dict[str, str], statement_timeout_ms: int | None) -> List[DbHandle]:
    handles: List[DbHandle] = []
    base_gid = f"apply_{uuid.uuid4().hex}"

    for shard_key, dsn in mapping.items():
        conn = psycopg2.connect(dsn)
        conn.autocommit = False

        with conn.cursor() as cur:
            # Опційно: таймаут, щоб інструмент не “висів” вічно
            if statement_timeout_ms is not None:
                cur.execute("SET statement_timeout = %s", (statement_timeout_ms,))

        # GID має бути унікальним у межах інстансу/кластера; додамо shard_key для надійності
        gid = f"{base_gid}_{shard_key}"
        handles.append(DbHandle(shard_key=shard_key, dsn=dsn, conn=conn, gid=gid))

    return handles


def prepare_everywhere(handles: List[DbHandle], sql_text: str) -> Tuple[bool, str | None]:
    """
    1) BEGIN (неявно через autocommit=False)
    2) execute SQL
    3) PREPARE TRANSACTION
    """
    for h in handles:
        try:
            with h.conn.cursor() as cur:
                cur.execute(sql_text)
                cur.execute("PREPARE TRANSACTION %s", (h.gid,))
            h.prepared = True
            # Після PREPARE транзакція завершена, але “заморожена” до COMMIT/ROLLBACK PREPARED
        except Exception as e:
            return False, f"[{h.shard_key}] failed: {e}"
    return True, None


def rollback_prepared(handles: List[DbHandle]) -> None:
    for h in handles:
        try:
            if h.prepared:
                # PREPARE вже завершив транзакцію, тому звичайний rollback не працює — треба ROLLBACK PREPARED
                with h.conn.cursor() as cur:
                    cur.execute("ROLLBACK PREPARED %s", (h.gid,))
            else:
                # Якщо не дійшли до PREPARE — просто rollback поточної транзакції
                h.conn.rollback()
        except Exception:
            # Тут навмисно “ковтаємо” винятки: ми в аварійному режимі і робимо best-effort cleanup
            pass


def commit_prepared(handles: List[DbHandle]) -> Tuple[bool, str | None]:
    """
    Фаза 2: COMMIT PREPARED на всіх.
    У нормі це або успішно на всіх, або (дуже рідко) збої інфраструктури/доступу.
    """
    for h in handles:
        try:
            with h.conn.cursor() as cur:
                cur.execute("COMMIT PREPARED %s", (h.gid,))
        except Exception as e:
            # Це “поганий” сценарій: частина вже могла закомітитися.
            return False, f"[{h.shard_key}] COMMIT PREPARED failed: {e}"
    return True, None


def close_all(handles: List[DbHandle]) -> None:
    for h in handles:
        try:
            h.conn.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply a DDL/DML SQL file to all 16 shard databases atomically (2PC)."
    )
    parser.add_argument("sql_file", help="Path to .sql file to execute on every DB")
    parser.add_argument(
        "--mapping",
        default=os.getenv("MAPPING_FILE", "mapping.json"),
        help="Path to mapping.json (default: $MAPPING_FILE or ./mapping.json)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=300_000,
        help="statement_timeout in ms for each DB session (default: 300000)",
    )

    args = parser.parse_args()

    mapping = load_mapping(args.mapping)
    sql_text = read_sql(args.sql_file)

    handles: List[DbHandle] = []
    try:
        handles = connect_all(mapping, args.timeout_ms)

        ok, err = prepare_everywhere(handles, sql_text)
        if not ok:
            rollback_prepared(handles)
            print(f"✗ Aborted. Rolled back everywhere. Reason: {err}", file=sys.stderr)
            return 2

        ok, err = commit_prepared(handles)
        if not ok:
            # На практиці дуже рідко, але важливо явно повідомити, що стан може бути частково закомічений
            print(
                "✗ Critical: commit phase failed. Some DBs may be committed while others not.\n"
                f"  Details: {err}",
                file=sys.stderr,
            )
            return 3

        print(f"✓ Applied successfully on {len(handles)} DBs (2PC)")
        return 0

    finally:
        close_all(handles)


if __name__ == "__main__":
    raise SystemExit(main())
