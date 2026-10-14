from typing import Optional

from fastapi import APIRouter

from ..database import DB
from ..schemas import (
    Fatura,
    OSCreate,
    OSDetalhe,
    OSPecaAdd,
    OSResumo,
    OSStatusUpdate,
    OSUpdate,
    StatusOS,
)
from ..services import ordens

router = APIRouter(prefix="/api/ordens-servico", tags=["Ordens de Serviço"])


@router.post("", response_model=OSDetalhe, status_code=201)
async def abrir_os(body: OSCreate, db: DB):
    os_id = await ordens.criar_os(db, body)
    return await ordens.obter_os(db, os_id)


@router.get("", response_model=list[OSResumo])
async def listar_os(db: DB, status: Optional[StatusOS] = None, q: Optional[str] = None):
    return await ordens.listar_os(db, status.value if status else None, q)


@router.get("/{os_id}", response_model=OSDetalhe)
async def obter_os(os_id: int, db: DB):
    return await ordens.obter_os(db, os_id)


@router.patch("/{os_id}", response_model=OSDetalhe)
async def editar_os(os_id: int, body: OSUpdate, db: DB):
    await ordens.atualizar_os(db, os_id, body.model_dump(exclude_unset=True))
    return await ordens.obter_os(db, os_id)


@router.patch("/{os_id}/status", response_model=OSDetalhe)
async def atualizar_status(os_id: int, body: OSStatusUpdate, db: DB):
    await ordens.atualizar_status(db, os_id, body.status.value)
    return await ordens.obter_os(db, os_id)


@router.post("/{os_id}/pecas", response_model=OSDetalhe, status_code=201)
async def adicionar_peca(os_id: int, body: OSPecaAdd, db: DB):
    await ordens.adicionar_peca(db, os_id, body.peca_id, body.quantidade)
    return await ordens.obter_os(db, os_id)


@router.delete("/{os_id}/pecas/{item_id}", response_model=OSDetalhe)
async def remover_peca(os_id: int, item_id: int, db: DB):
    await ordens.remover_peca(db, os_id, item_id)
    return await ordens.obter_os(db, os_id)


@router.get("/{os_id}/fatura", response_model=Fatura)
async def obter_fatura(os_id: int, db: DB):
    return await ordens.fatura(db, os_id)
