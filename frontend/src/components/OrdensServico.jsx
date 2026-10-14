import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { STATUS, STATUS_ORDER, dateTime, money } from '../utils.js';
import { useDebounce } from '../useDebounce.js';
import StatusBadge from './StatusBadge.jsx';
import OSModal from './OSModal.jsx';
import NovaOSModal from './NovaOSModal.jsx';
import { useToast } from './Toast.jsx';

export default function OrdensServico({ initialStatus = '' }) {
  const toast = useToast();
  const [status, setStatus] = useState(initialStatus);
  const [busca, setBusca] = useState('');
  const debouncedBusca = useDebounce(busca, 300); // 300 ms antes de consultar o backend
  const [lista, setLista] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selecionada, setSelecionada] = useState(null);
  const [criando, setCriando] = useState(false);

  useEffect(() => setStatus(initialStatus), [initialStatus]);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    api
      .listarOS({ status, q: debouncedBusca.trim() }, ctrl.signal)
      .then(setLista)
      .catch((e) => e.name !== 'AbortError' && toast(e.message, 'error'))
      .finally(() => !ctrl.signal.aborted && setLoading(false));
    return () => ctrl.abort();
  }, [status, debouncedBusca, toast]);

  // Mantém a linha da tabela sincronizada com alterações feitas no modal.
  const aplicarMudanca = (detalhe) =>
    setLista((l) =>
      l.map((o) =>
        o.id === detalhe.id
          ? { ...o, status: detalhe.status, valor_mao_de_obra: detalhe.valor_mao_de_obra,
              total_pecas: detalhe.total_pecas, total: detalhe.total, updated_at: detalhe.updated_at }
          : o
      )
    );

  return (
    <div className="stack">
      <div className="toolbar">
        <input
          className="input grow"
          type="search"
          placeholder="Buscar por cliente, equipamento ou nº da OS…"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filtrar por status">
          <option value="">Todos os status</option>
          {STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {STATUS[s].label}
            </option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={() => setCriando(true)}>
          + Nova OS
        </button>
      </div>

      <div className="card table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>OS</th>
              <th>Cliente</th>
              <th>Equipamento</th>
              <th className="hide-sm">Defeito relatado</th>
              <th>Status</th>
              <th className="num">Total</th>
              <th className="hide-sm">Atualizada</th>
            </tr>
          </thead>
          <tbody>
            {loading && lista.length === 0 ? (
              <tr><td colSpan="7" className="muted center">Carregando…</td></tr>
            ) : lista.length === 0 ? (
              <tr><td colSpan="7" className="muted center">Nenhuma ordem de serviço encontrada.</td></tr>
            ) : (
              lista.map((o) => (
                <tr key={o.id} className="clickable" onClick={() => setSelecionada(o.id)}>
                  <td>#{o.id}</td>
                  <td>{o.cliente_nome}</td>
                  <td>{o.equipamento}</td>
                  <td className="hide-sm truncate">{o.defeito_relatado}</td>
                  <td><StatusBadge status={o.status} /></td>
                  <td className="num">{money(o.total)}</td>
                  <td className="hide-sm muted">{dateTime(o.updated_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selecionada && (
        <OSModal osId={selecionada} onClose={() => setSelecionada(null)} onChanged={aplicarMudanca} />
      )}
      {criando && (
        <NovaOSModal
          onClose={() => setCriando(false)}
          onCreated={(os) => {
            setCriando(false);
            setLista((l) => [os, ...l]);
            setSelecionada(os.id);
            toast(`OS #${os.id} aberta com sucesso.`, 'success');
          }}
        />
      )}
    </div>
  );
}
