from typing import Optional

from fastapi import APIRouter, Query

from ..database import DB
from ..errors import AppError
from ..schemas import PecaIn, PecaOut
from ..utils import fetch_all, fetch_one

router = APIRouter(prefix="/api/pecas", tags=["Peças / Estoque"])


@router.get("/alerta-estoque", response_model=list[PecaOut])
async def alerta_estoque(db: DB):
    """Peças com quantidade_estoque <= estoque_minimo (as mais críticas primeiro)."""
    return await fetch_all(
        db,
        """SELECT * FROM pecas WHERE quantidade_estoque <= estoque_minimo
           ORDER BY (quantidade_estoque - estoque_minimo), nome""",
    )


@router.post("", response_model=PecaOut, status_code=201)
async def criar_peca(body: PecaIn, db: DB):
    cur = await db.execute(
        """INSERT INTO pecas (nome, preco_custo, preco_venda, quantidade_estoque, estoque_minimo)
           VALUES (?, ?, ?, ?, ?)""",
        (body.nome, body.preco_custo, body.preco_venda, body.quantidade_estoque, body.estoque_minimo),
    )
    return await fetch_one(db, "SELECT * FROM pecas WHERE id = ?", (cur.lastrowid,))


@router.get("", response_model=list[PecaOut])
async def listar_pecas(db: DB, q: Optional[str] = None, limit: int = Query(100, ge=1, le=500)):
    if q:
        return await fetch_all(
            db, "SELECT * FROM pecas WHERE nome LIKE ? ORDER BY nome LIMIT ?", (f"%{q}%", limit)
        )
    return await fetch_all(db, "SELECT * FROM pecas ORDER BY nome LIMIT ?", (limit,))


@router.get("/{peca_id}", response_model=PecaOut)
async def obter_peca(peca_id: int, db: DB):
    row = await fetch_one(db, "SELECT * FROM pecas WHERE id = ?", (peca_id,))
    if not row:
        raise AppError(404, "Peça não encontrada")
    return row


@router.put("/{peca_id}", response_model=PecaOut)
async def atualizar_peca(peca_id: int, body: PecaIn, db: DB):
    cur = await db.execute(
        """UPDATE pecas SET nome = ?, preco_custo = ?, preco_venda = ?,
                            quantidade_estoque = ?, estoque_minimo = ? WHERE id = ?""",
        (body.nome, body.preco_custo, body.preco_venda, body.quantidade_estoque, body.estoque_minimo, peca_id),
    )
    if cur.rowcount == 0:
        raise AppError(404, "Peça não encontrada")
    return await fetch_one(db, "SELECT * FROM pecas WHERE id = ?", (peca_id,))


@router.delete("/{peca_id}", status_code=204)
async def remover_peca(peca_id: int, db: DB):
    cur = await db.execute("DELETE FROM pecas WHERE id = ?", (peca_id,))
    if cur.rowcount == 0:
        raise AppError(404, "Peça não encontrada")
