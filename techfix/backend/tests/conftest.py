import os
import tempfile

# O banco de testes precisa ser definido ANTES de importar a aplicação.
_tmp = tempfile.mkdtemp(prefix="techfix_test_")
os.environ["TECHFIX_DB"] = os.path.join(_tmp, "test.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def cenario(client):
    """Cria cliente + equipamento + peça (estoque 5, mínimo 2) + OS com mão de obra 100."""
    cli = client.post(
        "/api/clientes", json={"nome": "Maria Silva", "telefone": "+244 923 456 789", "email": "maria@exemplo.com"}
    ).json()
    eq = client.post(
        "/api/equipamentos",
        json={"cliente_id": cli["id"], "tipo": "Notebook", "marca_modelo": "Dell XPS 13", "numero_serie": "SN123"},
    ).json()
    peca = client.post(
        "/api/pecas",
        json={"nome": "SSD 500GB", "preco_custo": "200.00", "preco_venda": "350.50",
              "quantidade_estoque": 5, "estoque_minimo": 2},
    ).json()
    os_ = client.post(
        "/api/ordens-servico",
        json={"equipamento_id": eq["id"], "defeito_relatado": "Não liga", "valor_mao_de_obra": "100.00"},
    ).json()
    return {"cliente": cli, "equipamento": eq, "peca": peca, "os": os_}
