import os
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Annotated, AsyncIterator

import aiosqlite
from fastapi import Depends

# Decimal não é um tipo nativo do sqlite3: gravamos como texto (coluna NUMERIC converte).
sqlite3.register_adapter(Decimal, str)

NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS clientes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    telefone    TEXT NOT NULL,
    email       TEXT,
    created_at  TEXT NOT NULL DEFAULT ({NOW_SQL})
);

CREATE TABLE IF NOT EXISTS equipamentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id    INTEGER NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    tipo          TEXT NOT NULL,
    marca_modelo  TEXT NOT NULL,
    numero_serie  TEXT
);

CREATE TABLE IF NOT EXISTS pecas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                TEXT NOT NULL,
    preco_custo         NUMERIC NOT NULL CHECK (preco_custo >= 0),
    preco_venda         NUMERIC NOT NULL CHECK (preco_venda >= 0),
    quantidade_estoque  INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_estoque >= 0),
    estoque_minimo      INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0)
);

CREATE TABLE IF NOT EXISTS ordens_servico (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id       INTEGER NOT NULL REFERENCES equipamentos(id) ON DELETE RESTRICT,
    defeito_relatado     TEXT NOT NULL,
    diagnostico_tecnico  TEXT,
    valor_mao_de_obra    NUMERIC NOT NULL DEFAULT 0 CHECK (valor_mao_de_obra >= 0),
    status               TEXT NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE','EM_ANALISE','AGUARDANDO_PECA','CONCLUIDO','ENTREGUE')),
    created_at           TEXT NOT NULL DEFAULT ({NOW_SQL}),
    updated_at           TEXT NOT NULL DEFAULT ({NOW_SQL})
);

CREATE TABLE IF NOT EXISTS os_pecas (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    os_id                    INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    peca_id                  INTEGER NOT NULL REFERENCES pecas(id) ON DELETE RESTRICT,
    quantidade_utilizada     INTEGER NOT NULL CHECK (quantidade_utilizada > 0),
    preco_unitario_aplicado  NUMERIC NOT NULL CHECK (preco_unitario_aplicado >= 0)
);

CREATE INDEX IF NOT EXISTS idx_equipamentos_cliente ON equipamentos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_os_equipamento ON ordens_servico(equipamento_id);
CREATE INDEX IF NOT EXISTS idx_os_status ON ordens_servico(status);
CREATE INDEX IF NOT EXISTS idx_os_pecas_os ON os_pecas(os_id);
"""


def db_path() -> str:
    default = Path(__file__).resolve().parent.parent / "techfix.db"
    return os.environ.get("TECHFIX_DB", str(default))


async def _connect() -> aiosqlite.Connection:
    # isolation_level=None => modo autocommit: as transações são controladas
    # explicitamente com BEGIN / COMMIT / ROLLBACK no serviço.
    db = await aiosqlite.connect(db_path(), isolation_level=None)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    return db


async def init_db() -> None:
    db = await _connect()
    try:
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.executescript(SCHEMA)
    finally:
        await db.close()


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await _connect()
    try:
        yield db
    finally:
        await db.close()


DB = Annotated[aiosqlite.Connection, Depends(get_db)]
