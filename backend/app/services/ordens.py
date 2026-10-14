from contextlib import asynccontextmanager
from decimal import Decimal

import aiosqlite

from ..database import NOW_SQL
from ..errors import AppError
from ..utils import D, fetch_all, fetch_one

BASE_OS_SQL = """
SELECT os.id, os.equipamento_id, os.defeito_relatado, os.diagnostico_tecnico,
       os.valor_mao_de_obra, os.status, os.created_at, os.updated_at,
       c.id AS cliente_id, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
       e.tipo AS equipamento_tipo, e.marca_modelo, e.numero_serie,
       COALESCE((SELECT ROUND(SUM(op.quantidade_utilizada * op.preco_unitario_aplicado), 2)
                 FROM os_pecas op WHERE op.os_id = os.id), 0) AS total_pecas
FROM ordens_servico os
JOIN equipamentos e ON e.id = os.equipamento_id
JOIN clientes c ON c.id = e.cliente_id
"""


@asynccontextmanager
async def transacao(db: aiosqlite.Connection):
    """BEGIN ... COMMIT com ROLLBACK automático em qualquer exceção.

    BEGIN IMMEDIATE adquire o lock de escrita logo no início, evitando que duas
    requisições concorrentes leiam o mesmo saldo de estoque.
    """
    await db.execute("BEGIN IMMEDIATE")
    try:
        yield
        await db.execute("COMMIT")
    except Exception:
        if db.in_transaction:
            await db.execute("ROLLBACK")
        raise


def _montar_resumo(row: dict) -> dict:
    mao_de_obra = D(row["valor_mao_de_obra"])
    total_pecas = D(row["total_pecas"])
    return {
        **row,
        "equipamento": f"{row['equipamento_tipo']} · {row['marca_modelo']}",
        "valor_mao_de_obra": mao_de_obra,
        "total_pecas": total_pecas,
        "total": mao_de_obra + total_pecas,
    }


async def listar_itens(db: aiosqlite.Connection, os_id: int) -> list[dict]:
    rows = await fetch_all(
        db,
        """SELECT op.id, op.peca_id, p.nome AS peca_nome, op.quantidade_utilizada,
                  op.preco_unitario_aplicado
           FROM os_pecas op JOIN pecas p ON p.id = op.peca_id
           WHERE op.os_id = ? ORDER BY op.id""",
        (os_id,),
    )
    for r in rows:
        r["preco_unitario_aplicado"] = D(r["preco_unitario_aplicado"])
        r["subtotal"] = r["preco_unitario_aplicado"] * r["quantidade_utilizada"]
    return rows


async def listar_os(db: aiosqlite.Connection, status: str | None, q: str | None) -> list[dict]:
    where, params = [], []
    if status:
        where.append("os.status = ?")
        params.append(status)
    if q:
        like = f"%{q}%"
        where.append("(c.nome LIKE ? OR e.marca_modelo LIKE ? OR CAST(os.id AS TEXT) = ?)")
        params += [like, like, q.lstrip("#")]
    sql = BASE_OS_SQL + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY os.id DESC"
    return [_montar_resumo(r) for r in await fetch_all(db, sql, params)]


async def obter_os(db: aiosqlite.Connection, os_id: int) -> dict:
    row = await fetch_one(db, BASE_OS_SQL + " WHERE os.id = ?", (os_id,))
    if not row:
        raise AppError(404, "Ordem de serviço não encontrada")
    detalhe = _montar_resumo(row)
    detalhe["itens"] = await listar_itens(db, os_id)
    return detalhe


async def fatura(db: aiosqlite.Connection, os_id: int) -> dict:
    os_ = await obter_os(db, os_id)
    return {
        "os_id": os_id,
        "valor_mao_de_obra": os_["valor_mao_de_obra"],
        "total_pecas": os_["total_pecas"],
        "total": os_["total"],
        "itens": os_["itens"],
    }


async def criar_os(db: aiosqlite.Connection, dados) -> int:
    if not await fetch_one(db, "SELECT id FROM equipamentos WHERE id = ?", (dados.equipamento_id,)):
        raise AppError(404, "Equipamento não encontrado")
    cur = await db.execute(
        """INSERT INTO ordens_servico
           (equipamento_id, defeito_relatado, diagnostico_tecnico, valor_mao_de_obra)
           VALUES (?, ?, ?, ?)""",
        (dados.equipamento_id, dados.defeito_relatado, dados.diagnostico_tecnico, dados.valor_mao_de_obra),
    )
    return cur.lastrowid


async def atualizar_os(db: aiosqlite.Connection, os_id: int, campos: dict) -> None:
    sets = ", ".join(f"{c} = ?" for c in campos)
    cur = await db.execute(
        f"UPDATE ordens_servico SET {sets}, updated_at = {NOW_SQL} WHERE id = ?",
        [*campos.values(), os_id],
    )
    if cur.rowcount == 0:
        raise AppError(404, "Ordem de serviço não encontrada")


async def atualizar_status(db: aiosqlite.Connection, os_id: int, status: str) -> None:
    cur = await db.execute(
        f"UPDATE ordens_servico SET status = ?, updated_at = {NOW_SQL} WHERE id = ?",
        (status, os_id),
    )
    if cur.rowcount == 0:
        raise AppError(404, "Ordem de serviço não encontrada")


async def _tocar_os(db: aiosqlite.Connection, os_id: int) -> None:
    await db.execute(f"UPDATE ordens_servico SET updated_at = {NOW_SQL} WHERE id = ?", (os_id,))


async def adicionar_peca(db: aiosqlite.Connection, os_id: int, peca_id: int, quantidade: int) -> None:
    """Adiciona peça à OS e baixa o estoque, tudo na MESMA transação.

    Se faltar estoque (ou qualquer passo falhar), nada é gravado (ROLLBACK).
    """
    async with transacao(db):
        os_ = await fetch_one(db, "SELECT id, status FROM ordens_servico WHERE id = ?", (os_id,))
        if not os_:
            raise AppError(404, "Ordem de serviço não encontrada")
        if os_["status"] == "ENTREGUE":
            raise AppError(400, "Não é possível alterar peças de uma OS já entregue")

        peca = await fetch_one(
            db, "SELECT id, nome, preco_venda, quantidade_estoque FROM pecas WHERE id = ?", (peca_id,)
        )
        if not peca:
            raise AppError(404, "Peça não encontrada")

        cur = await db.execute(
            """UPDATE pecas SET quantidade_estoque = quantidade_estoque - ?
               WHERE id = ? AND quantidade_estoque >= ?""",
            (quantidade, peca_id, quantidade),
        )
        if cur.rowcount == 0:
            raise AppError(
                400,
                f"Estoque insuficiente para '{peca['nome']}': "
                f"disponível {peca['quantidade_estoque']}, solicitado {quantidade}",
            )

        await db.execute(
            """INSERT INTO os_pecas (os_id, peca_id, quantidade_utilizada, preco_unitario_aplicado)
               VALUES (?, ?, ?, ?)""",
            (os_id, peca_id, quantidade, Decimal(str(peca["preco_venda"]))),
        )
        await _tocar_os(db, os_id)


async def remover_peca(db: aiosqlite.Connection, os_id: int, item_id: int) -> None:
    """Remove a peça da OS e devolve a quantidade ao estoque (transação única)."""
    async with transacao(db):
        os_ = await fetch_one(db, "SELECT id, status FROM ordens_servico WHERE id = ?", (os_id,))
        if not os_:
            raise AppError(404, "Ordem de serviço não encontrada")
        if os_["status"] == "ENTREGUE":
            raise AppError(400, "Não é possível alterar peças de uma OS já entregue")

        item = await fetch_one(
            db, "SELECT id, peca_id, quantidade_utilizada FROM os_pecas WHERE id = ? AND os_id = ?",
            (item_id, os_id),
        )
        if not item:
            raise AppError(404, "Item não encontrado nesta OS")

        await db.execute(
            "UPDATE pecas SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?",
            (item["quantidade_utilizada"], item["peca_id"]),
        )
        await db.execute("DELETE FROM os_pecas WHERE id = ?", (item_id,))
        await _tocar_os(db, os_id)
