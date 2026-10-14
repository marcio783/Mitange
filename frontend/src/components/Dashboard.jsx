import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { STATUS, STATUS_ORDER, money } from '../utils.js';
import { useToast } from './Toast.jsx';

function Metric({ label, value, tone }) {
  return (
    <div className={`card metric metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
    </div>
  );
}

export default function Dashboard({ onOpenOS }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    api
      .dashboard(ctrl.signal)
      .then(setData)
      .catch((e) => e.name !== 'AbortError' && toast(e.message, 'error'))
      .finally(() => !ctrl.signal.aborted && setLoading(false));
    return () => ctrl.abort();
  }, [toast]);

  if (loading) return <p className="muted">Carregando painel…</p>;
  if (!data) return <p className="muted">Não foi possível carregar o painel.</p>;

  const maxStatus = Math.max(1, ...Object.values(data.por_status));

  return (
    <div className="stack">
      <section className="grid-3">
        <Metric label="OS abertas" value={data.os_abertas} tone="orange" />
        <Metric label="OS concluídas no mês" value={data.os_concluidas_mes} tone="green" />
        <Metric label="Faturamento do mês" value={money(data.faturamento_mes)} tone="blue" />
      </section>

      <section className="grid-2">
        <div className="card">
          <h3>Alertas de estoque baixo</h3>
          {data.alertas_estoque.length === 0 ? (
            <p className="muted">Nenhuma peça abaixo do estoque mínimo. 👍</p>
          ) : (
            <ul className="alert-list">
              {data.alertas_estoque.map((p) => {
                const zerado = p.quantidade_estoque === 0;
                return (
                  <li key={p.id} className={zerado ? 'alert alert-critical' : 'alert'}>
                    <div>
                      <strong>{p.nome}</strong>
                      <small>Mínimo: {p.estoque_minimo}</small>
                    </div>
                    <span className="stock-pill">{zerado ? 'Esgotada' : `${p.quantidade_estoque} em estoque`}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="card">
          <h3>Ordens por status</h3>
          <ul className="status-bars">
            {STATUS_ORDER.map((s) => (
              <li key={s}>
                <button className="link-row" onClick={() => onOpenOS(s)} title="Ver ordens deste status">
                  <span className={`dot dot-${STATUS[s].cls}`} />
                  <span className="grow">{STATUS[s].label}</span>
                  <strong>{data.por_status[s]}</strong>
                </button>
                <div className="bar">
                  <div className={`bar-fill dot-${STATUS[s].cls}`} style={{ width: `${(data.por_status[s] / maxStatus) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
