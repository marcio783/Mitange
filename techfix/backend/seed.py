"""Popula o banco com dados de demonstração.  Uso:  python seed.py"""
import asyncio
from decimal import Decimal

from app.database import _connect, init_db
from app.schemas import OSCreate
from app.services import ordens

CLIENTES = [
    ("Maria Silva", "+244 923 456 789", "maria@exemplo.com"),
    ("João Pereira", "+244 912 345 678", "joao@exemplo.com"),
    ("Ana Costa", "+244 934 567 890", None),
    ("Carlos Mendes", "+244 945 678 901", "carlos@exemplo.com"),
]
EQUIPAMENTOS = [
    (1, "Notebook", "Dell XPS 13", "SN-DELL-001"),
    (2, "Smartphone", "Samsung Galaxy S21", "IMEI-3521"),
    (3, "Notebook", "Lenovo ThinkPad T14", "SN-LEN-778"),
    (4, "Tablet", "iPad 9ª geração", "SN-IPAD-42"),
    (1, "Smartphone", "iPhone 12", "IMEI-9910"),
]
PECAS = [  # nome, custo, venda, estoque, mínimo
    ("SSD 500GB NVMe", "200.00", "350.50", 8, 3),
    ("Memória RAM 8GB DDR4", "90.00", "160.00", 2, 4),
    ("Tela LCD 13.3\"", "400.00", "650.00", 3, 3),
    ("Bateria Notebook Universal", "120.00", "220.00", 10, 4),
    ("Tela OLED Smartphone", "300.00", "520.00", 1, 2),
    ("Conector de Carga USB-C", "15.00", "45.00", 25, 10),
    ("Pasta Térmica 4g", "5.00", "20.00", 40, 10),
]
OS = [  # equip_id, defeito, diag, mão de obra, status, [(peca_id, qtd)]
    (1, "Notebook não liga", "Fonte e SSD com defeito", "120.00", "AGUARDANDO_PECA", []),
    (2, "Tela quebrada", "Troca de tela", "80.00", "EM_ANALISE", []),
    (3, "Superaquecimento", "Limpeza e troca de pasta térmica", "60.00", "CONCLUIDO", [(7, 1)]),
    (4, "Não carrega", "Conector USB-C danificado", "50.00", "ENTREGUE", [(6, 1)]),
    (5, "Bateria viciada", None, "40.00", "PENDENTE", []),
    (1, "Lentidão extrema", "Troca de HDD por SSD", "90.00", "CONCLUIDO", [(1, 1), (2, 1)]),
]


async def main():
    await init_db()
    db = await _connect()
    try:
        if (await (await db.execute("SELECT COUNT(*) FROM clientes")).fetchone())[0]:
            print("Banco já possui dados; nada a fazer.")
            return
        for c in CLIENTES:
            await db.execute("INSERT INTO clientes (nome, telefone, email) VALUES (?,?,?)", c)
        for e in EQUIPAMENTOS:
            await db.execute(
                "INSERT INTO equipamentos (cliente_id, tipo, marca_modelo, numero_serie) VALUES (?,?,?,?)", e
            )
        for n, c, v, q, m in PECAS:
            await db.execute(
                "INSERT INTO pecas (nome, preco_custo, preco_venda, quantidade_estoque, estoque_minimo) "
                "VALUES (?,?,?,?,?)",
                (n, Decimal(c), Decimal(v), q, m),
            )
        for eq, defeito, diag, mo, status, pecas in OS:
            os_id = await ordens.criar_os(
                db,
                OSCreate(equipamento_id=eq, defeito_relatado=defeito, diagnostico_tecnico=diag, valor_mao_de_obra=mo),
            )
            for peca_id, qtd in pecas:
                await ordens.adicionar_peca(db, os_id, peca_id, qtd)
            await ordens.atualizar_status(db, os_id, status)
        print("Dados de demonstração criados.")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
