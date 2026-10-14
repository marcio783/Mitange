# TechFix Pro — Gestão de Assistência Técnica & Estoque

Backend **FastAPI + SQLite3 (aiosqlite)** e frontend **React (Vite)**.

## Como executar

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                      # (opcional) dados de demonstração
uvicorn app.main:app --reload       # http://127.0.0.1:8000  (docs em /docs)
pytest                              # testes
```
O arquivo do banco é `backend/techfix.db` (altere com a variável `TECHFIX_DB`).

### Frontend
```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173 (proxy /api -> :8000)
```

## Estrutura
```
backend/app/
  database.py        # schema SQLite, PRAGMA foreign_keys = ON, conexão por requisição
  schemas.py         # Pydantic v2 (validação de telefone/e-mail, enums, dinheiro)
  services/ordens.py # regras de negócio e TRANSAÇÕES (BEGIN IMMEDIATE / COMMIT / ROLLBACK)
  routers/           # clientes, equipamentos, pecas, ordens, dashboard
backend/tests/       # pytest: validação, estoque, rollback, fatura, dashboard
frontend/src/
  components/        # Dashboard, OrdensServico, OSModal, NovaOSModal, Toast...
  useDebounce.js     # debounce de 300 ms (busca de clientes, peças e OS)
```

## Endpoints principais
| Método | Rota | Descrição |
|---|---|---|
| CRUD | `/api/clientes`, `/api/equipamentos`, `/api/pecas` | Cadastros (`?q=` busca por texto) |
| GET | `/api/pecas/alerta-estoque` | Peças com `quantidade_estoque <= estoque_minimo` |
| POST | `/api/ordens-servico` | Abre OS |
| GET | `/api/ordens-servico?status=&q=` | Lista/filtra OS |
| POST | `/api/ordens-servico/{id}/pecas` | Adiciona peça **e baixa estoque na mesma transação**; sem estoque → `400` + ROLLBACK |
| DELETE | `/api/ordens-servico/{id}/pecas/{item_id}` | Remove peça e devolve ao estoque |
| PATCH | `/api/ordens-servico/{id}/status` | Atualiza status |
| PATCH | `/api/ordens-servico/{id}` | Edita diagnóstico / mão de obra |
| GET | `/api/ordens-servico/{id}/fatura` | Mão de obra + peças = total |
| GET | `/api/dashboard` | Métricas e alertas de estoque |

## Decisões de projeto
- **Atomicidade:** `adicionar_peca` abre `BEGIN IMMEDIATE` (lock de escrita antecipado, sem corrida de estoque), faz o `UPDATE ... WHERE quantidade_estoque >= ?`, insere em `os_pecas` e confirma com `COMMIT`; qualquer exceção dispara `ROLLBACK`.
- **Preço congelado:** `preco_unitario_aplicado` guarda o preço de venda no momento da adição; reajustes futuros não alteram OS antigas.
- **Dinheiro:** `Decimal` na API (2 casas), colunas `NUMERIC`; JSON de saída em número.
- **Regras extras:** OS `ENTREGUE` não permite alterar peças; peça/cliente/equipamento em uso não podem ser excluídos (`409`).
- **"Concluídas no mês" / faturamento:** OS `CONCLUIDO` ou `ENTREGUE` cuja `updated_at` está no mês corrente.
- **Moeda exibida:** `frontend/src/utils.js` (`CURRENCY`, padrão AOA/pt-AO).
- **Erros no UI:** falhas da API (ex.: estoque insuficiente) viram toast; o estado do React não é alterado.
