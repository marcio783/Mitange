from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional, Sequence

import aiosqlite

CENT = Decimal("0.01")


def D(value: Any) -> Decimal:
    """Converte valores vindos do SQLite (int/float/str/None) em Decimal com 2 casas."""
    return Decimal(str(value if value is not None else 0)).quantize(CENT, rounding=ROUND_HALF_UP)


async def fetch_one(db: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()) -> Optional[dict]:
    cur = await db.execute(sql, params)
    row = await cur.fetchone()
    await cur.close()
    return dict(row) if row else None


async def fetch_all(db: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()) -> list[dict]:
    cur = await db.execute(sql, params)
    rows = await cur.fetchall()
    await cur.close()
    return [dict(r) for r in rows]
