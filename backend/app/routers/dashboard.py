from fastapi import APIRouter

from ..database import DB
from ..schemas import Dashboard
from ..utils import D, fetch_all, fetch_one

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

MES_ATUAL = "strftime('%Y-%m', os.updated_at) = strftime('%Y-%m', 'now')"


@router.get("", response_model=Dashboard)
async def dashboard(db: DB):
    abertas = await fetch_one(
        db, "SELECT COUNT(*) AS n FROM ordens_servico WHERE status NOT IN ('CONCLUIDO', 'ENTREGUE')"
    )
    mes = await fetch_one(
        db,
        f"""SELECT COUNT(*) AS n,
                   COALESCE(SUM(os.valor_mao_de_obra + COALESCE(
                       (SELECT SUM(op.quantidade_utilizada * op.preco_unitario_aplicado)
                        FROM os_pecas op WHERE op.os_id = os.id), 0)), 0) AS total
            FROM ordens_servico os
            WHERE os.status IN ('CONCLUIDO', 'ENTREGUE') AND {MES_ATUAL}""",
    )
    por_status = {s: 0 for s in ("PENDENTE", "EM_ANALISE", "AGUARDANDO_PECA", "CONCLUIDO", "ENTREGUE")}
    for r in await fetch_all(db, "SELECT status, COUNT(*) AS n FROM ordens_servico GROUP BY status"):
        por_status[r["status"]] = r["n"]
    alertas = await fetch_all(
        db,
        """SELECT * FROM pecas WHERE quantidade_estoque <= estoque_minimo
           ORDER BY (quantidade_estoque - estoque_minimo), nome""",
    )
    return {
        "os_abertas": abertas["n"],
        "os_concluidas_mes": mes["n"],
        "faturamento_mes": D(mes["total"]),
        "por_status": por_status,
        "alertas_estoque": alertas,
    }
