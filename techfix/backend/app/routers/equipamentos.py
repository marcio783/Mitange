from typing import Optional

from fastapi import APIRouter

from ..database import DB
from ..errors import AppError
from ..schemas import EquipamentoIn, EquipamentoOut
from ..utils import fetch_all, fetch_one

router = APIRouter(prefix="/api/equipamentos", tags=["Equipamentos"])

SELECT = """SELECT e.*, c.nome AS cliente_nome
            FROM equipamentos e JOIN clientes c ON c.id = e.cliente_id"""


async def _garantir_cliente(db, cliente_id: int):
    if not await fetch_one(db, "SELECT id FROM clientes WHERE id = ?", (cliente_id,)):
        raise AppError(404, "Cliente não encontrado")


@router.post("", response_model=EquipamentoOut, status_code=201)
async def criar_equipamento(body: EquipamentoIn, db: DB):
    await _garantir_cliente(db, body.cliente_id)
    cur = await db.execute(
        "INSERT INTO equipamentos (cliente_id, tipo, marca_modelo, numero_serie) VALUES (?, ?, ?, ?)",
        (body.cliente_id, body.tipo, body.marca_modelo, body.numero_serie),
    )
    return await fetch_one(db, SELECT + " WHERE e.id = ?", (cur.lastrowid,))


@router.get("", response_model=list[EquipamentoOut])
async def listar_equipamentos(db: DB, cliente_id: Optional[int] = None):
    if cliente_id is not None:
        return await fetch_all(db, SELECT + " WHERE e.cliente_id = ? ORDER BY e.id DESC", (cliente_id,))
    return await fetch_all(db, SELECT + " ORDER BY e.id DESC")


@router.get("/{equipamento_id}", response_model=EquipamentoOut)
async def obter_equipamento(equipamento_id: int, db: DB):
    row = await fetch_one(db, SELECT + " WHERE e.id = ?", (equipamento_id,))
    if not row:
        raise AppError(404, "Equipamento não encontrado")
    return row


@router.put("/{equipamento_id}", response_model=EquipamentoOut)
async def atualizar_equipamento(equipamento_id: int, body: EquipamentoIn, db: DB):
    await _garantir_cliente(db, body.cliente_id)
    cur = await db.execute(
        "UPDATE equipamentos SET cliente_id = ?, tipo = ?, marca_modelo = ?, numero_serie = ? WHERE id = ?",
        (body.cliente_id, body.tipo, body.marca_modelo, body.numero_serie, equipamento_id),
    )
    if cur.rowcount == 0:
        raise AppError(404, "Equipamento não encontrado")
    return await fetch_one(db, SELECT + " WHERE e.id = ?", (equipamento_id,))


@router.delete("/{equipamento_id}", status_code=204)
async def remover_equipamento(equipamento_id: int, db: DB):
    cur = await db.execute("DELETE FROM equipamentos WHERE id = ?", (equipamento_id,))
    if cur.rowcount == 0:
        raise AppError(404, "Equipamento não encontrado")
