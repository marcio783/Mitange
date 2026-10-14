from typing import Optional

from fastapi import APIRouter, Query

from ..database import DB
from ..errors import AppError
from ..schemas import ClienteIn, ClienteOut
from ..utils import fetch_all, fetch_one

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


@router.post("", response_model=ClienteOut, status_code=201)
async def criar_cliente(body: ClienteIn, db: DB):
    cur = await db.execute(
        "INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)",
        (body.nome, body.telefone, body.email),
    )
    return await fetch_one(db, "SELECT * FROM clientes WHERE id = ?", (cur.lastrowid,))


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(db: DB, q: Optional[str] = None, limit: int = Query(100, ge=1, le=500)):
    if q:
        like = f"%{q}%"
        return await fetch_all(
            db,
            "SELECT * FROM clientes WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ? "
            "ORDER BY nome LIMIT ?",
            (like, like, like, limit),
        )
    return await fetch_all(db, "SELECT * FROM clientes ORDER BY nome LIMIT ?", (limit,))


@router.get("/{cliente_id}", response_model=ClienteOut)
async def obter_cliente(cliente_id: int, db: DB):
    row = await fetch_one(db, "SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    if not row:
        raise AppError(404, "Cliente não encontrado")
    return row


@router.put("/{cliente_id}", response_model=ClienteOut)
async def atualizar_cliente(cliente_id: int, body: ClienteIn, db: DB):
    cur = await db.execute(
        "UPDATE clientes SET nome = ?, telefone = ?, email = ? WHERE id = ?",
        (body.nome, body.telefone, body.email, cliente_id),
    )
    if cur.rowcount == 0:
        raise AppError(404, "Cliente não encontrado")
    return await fetch_one(db, "SELECT * FROM clientes WHERE id = ?", (cliente_id,))


@router.delete("/{cliente_id}", status_code=204)
async def remover_cliente(cliente_id: int, db: DB):
    # Se houver equipamentos vinculados, a FK (RESTRICT) gera IntegrityError -> 409.
    cur = await db.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    if cur.rowcount == 0:
        raise AppError(404, "Cliente não encontrado")
