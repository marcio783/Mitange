import sqlite3

import pytest

from app.database import db_path
from app.services import ordens


def estoque(client, peca_id):
    return client.get(f"/api/pecas/{peca_id}").json()["quantidade_estoque"]


def contar_itens(os_id):
    con = sqlite3.connect(db_path())
    try:
        return con.execute("SELECT COUNT(*) FROM os_pecas WHERE os_id = ?", (os_id,)).fetchone()[0]
    finally:
        con.close()


# ----------------------------------------------------------------- validação
def test_telefone_e_email_invalidos(client):
    r = client.post("/api/clientes", json={"nome": "Ana", "telefone": "abc", "email": "ana@exemplo.com"})
    assert r.status_code == 422
    r = client.post("/api/clientes", json={"nome": "Ana", "telefone": "923456789", "email": "invalido"})
    assert r.status_code == 422
    r = client.post("/api/clientes", json={"nome": "Ana", "telefone": "12", "email": None})
    assert r.status_code == 422


def test_crud_cliente_e_fk(client, cenario):
    cid = cenario["cliente"]["id"]
    assert client.put(f"/api/clientes/{cid}", json={"nome": "Maria S.", "telefone": "923456789"}).status_code == 200
    # cliente com equipamento não pode ser removido
    assert client.delete(f"/api/clientes/{cid}").status_code == 409
    assert client.post(
        "/api/equipamentos", json={"cliente_id": 9999, "tipo": "Notebook", "marca_modelo": "X"}
    ).status_code == 404


# ------------------------------------------------------------------- estoque
def test_adicionar_peca_baixa_estoque_e_fatura(client, cenario):
    os_id, peca_id = cenario["os"]["id"], cenario["peca"]["id"]
    r = client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca_id, "quantidade": 3})
    assert r.status_code == 201
    assert estoque(client, peca_id) == 2

    fatura = client.get(f"/api/ordens-servico/{os_id}/fatura").json()
    assert fatura["valor_mao_de_obra"] == 100.0
    assert fatura["total_pecas"] == 1051.5  # 3 x 350.50
    assert fatura["total"] == 1151.5

    # estoque (2) <= mínimo (2) -> aparece no alerta
    alertas = client.get("/api/pecas/alerta-estoque").json()
    assert any(p["id"] == peca_id for p in alertas)


def test_estoque_insuficiente_faz_rollback(client, cenario):
    os_id, peca_id = cenario["os"]["id"], cenario["peca"]["id"]
    r = client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca_id, "quantidade": 6})
    assert r.status_code == 400
    assert "Estoque insuficiente" in r.json()["detail"]
    assert estoque(client, peca_id) == 5
    assert contar_itens(os_id) == 0


def test_falha_no_meio_da_transacao_desfaz_baixa(client, cenario, monkeypatch):
    """Se algo falha DEPOIS do UPDATE de estoque, a baixa precisa ser revertida."""
    os_id, peca_id = cenario["os"]["id"], cenario["peca"]["id"]

    async def explode(*_a, **_k):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(ordens, "_tocar_os", explode)
    r = client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca_id, "quantidade": 2})
    assert r.status_code == 500
    assert r.json()["detail"] == "Erro interno do servidor. Tente novamente mais tarde."
    assert estoque(client, peca_id) == 5
    assert contar_itens(os_id) == 0


def test_remover_peca_devolve_estoque(client, cenario):
    os_id, peca_id = cenario["os"]["id"], cenario["peca"]["id"]
    det = client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca_id, "quantidade": 2}).json()
    item_id = det["itens"][0]["id"]
    assert estoque(client, peca_id) == 3
    r = client.delete(f"/api/ordens-servico/{os_id}/pecas/{item_id}")
    assert r.status_code == 200 and r.json()["itens"] == []
    assert estoque(client, peca_id) == 5


def test_preco_aplicado_nao_muda_com_reajuste(client, cenario):
    os_id, peca = cenario["os"]["id"], cenario["peca"]
    client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca["id"], "quantidade": 1})
    client.put(
        f"/api/pecas/{peca['id']}",
        json={"nome": peca["nome"], "preco_custo": 300, "preco_venda": 999, "quantidade_estoque": 4, "estoque_minimo": 2},
    )
    assert client.get(f"/api/ordens-servico/{os_id}/fatura").json()["total_pecas"] == 350.5


# ------------------------------------------------------------- status & lista
def test_status_filtros_e_entregue_bloqueia_pecas(client, cenario):
    os_id, peca_id = cenario["os"]["id"], cenario["peca"]["id"]
    assert client.patch(f"/api/ordens-servico/{os_id}/status", json={"status": "INVALIDO"}).status_code == 422
    r = client.patch(f"/api/ordens-servico/{os_id}/status", json={"status": "EM_ANALISE"})
    assert r.status_code == 200 and r.json()["status"] == "EM_ANALISE"

    assert any(o["id"] == os_id for o in client.get("/api/ordens-servico?status=EM_ANALISE").json())
    assert not any(o["id"] == os_id for o in client.get("/api/ordens-servico?status=PENDENTE").json())
    assert any(o["id"] == os_id for o in client.get("/api/ordens-servico?q=maria").json())

    client.patch(f"/api/ordens-servico/{os_id}/status", json={"status": "ENTREGUE"})
    r = client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca_id, "quantidade": 1})
    assert r.status_code == 400


def test_dashboard(client, cenario):
    os_id, peca_id = cenario["os"]["id"], cenario["peca"]["id"]
    client.post(f"/api/ordens-servico/{os_id}/pecas", json={"peca_id": peca_id, "quantidade": 1})
    antes = client.get("/api/dashboard").json()
    client.patch(f"/api/ordens-servico/{os_id}/status", json={"status": "CONCLUIDO"})
    depois = client.get("/api/dashboard").json()
    assert depois["os_abertas"] == antes["os_abertas"] - 1
    assert depois["os_concluidas_mes"] == antes["os_concluidas_mes"] + 1
    assert depois["faturamento_mes"] >= antes["faturamento_mes"] + 450.5


def test_os_inexistente(client):
    assert client.get("/api/ordens-servico/99999").status_code == 404
    assert client.get("/api/ordens-servico/99999/fatura").status_code == 404
    assert client.post("/api/ordens-servico/99999/pecas", json={"peca_id": 1, "quantidade": 1}).status_code == 404
