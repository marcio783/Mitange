import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { STATUS, STATUS_ORDER, dateTime, money } from '../utils.js';
import { useDebounce } from '../useDebounce.js';
import Modal from './Modal.jsx';
import StatusBadge from './StatusBadge.jsx';
import { useToast } from './Toast.jsx';

export default function OSModal({ osId, onClose, onChanged }) {
  const toast = useToast();
  const [os, setOs] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [salvando, setSalvando] = useState(false);

  // campos editáveis
  const [maoDeObra, setMaoDeObra] = useState('');
  const [diagnostico, setDiagnostico] = useState('');

  // busca de peças (debounce 300 ms)
  const [termo, setTermo] = useState('');
  const termoDebounced = useDebounce(termo, 300);
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [recarga, setRecarga] = useState(0);
  const [qtd, setQtd] = useState({});
  const [adicionando, setAdicionando] = useState(null);

  const aplicar = useCallback(
    (detalhe) => {
      setOs(detalhe);
      setMaoDeObra(String(detalhe.valor_mao_de_obra));
      setDiagnostico(detalhe.diagnostico_tecnico ?? '');
      onChanged?.(detalhe);
    },
    [onChanged]
  );

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .obterOS(osId, ctrl.signal)
      .then((d) => {
        setOs(d);
        setMaoDeObra(String(d.valor_mao_de_obra));
        setDiagnostico(d.diagnostico_tecnico ?? '');
      })
      .catch((e) => e.name !== 'AbortError' && setErroCarga(e.message));
    return () => ctrl.abort();
  }, [osId]);

  useEffect(() => {
    const ctrl = new AbortController();
    setBuscando(true);
    api
      .pecas(termoDebounced.trim(), ctrl.signal)
      .then(setResultados)
      .catch((e) => e.name !== 'AbortError' && toast(e.message, 'error'))
      .finally(() => !ctrl.signal.aborted && setBuscando(false));
    return () => ctrl.abort();
  }, [termoDebounced, recarga, toast]);

  const bloqueada = os?.status === 'ENTREGUE';

  async function mudarStatus(novo) {
    setSalvando(true);
    try {
      aplicar(await api.atualizarStatus(osId, novo));
      toast(`Status alterado para "${STATUS[novo].label}".`, 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSalvando(false);
    }
  }

  async function salvarDados() {
    const valor = Number(String(maoDeObra).replace(',', '.'));
    if (!Number.isFinite(valor) || valor < 0) {
      toast('Informe um valor de mão de obra válido (≥ 0).', 'error');
      return;
    }
    setSalvando(true);
    try {
      aplicar(await api.editarOS(osId, { valor_mao_de_obra: valor, diagnostico_tecnico: diagnostico.trim() || null }));
      toast('Dados da OS atualizados.', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSalvando(false);
    }
  }

  async function adicionarPeca(peca) {
    const quantidade = Number(qtd[peca.id] ?? 1);
    if (!Number.isInteger(quantidade) || quantidade < 1) {
      toast('Informe uma quantidade inteira maior que zero.', 'error');
      return;
    }
    setAdicionando(peca.id);
    try {
      aplicar(await api.adicionarPeca(osId, { peca_id: peca.id, quantidade }));
      toast(`${quantidade}× ${peca.nome} adicionada à OS.`, 'success');
    } catch (e) {
      // Ex.: 400 "Estoque insuficiente…" — mostramos o aviso e mantemos o estado da tela intacto.
      toast(e.message, 'error');
    } finally {
      setAdicionando(null);
      setRecarga((n) => n + 1); // atualiza o estoque exibido nos resultados
    }
  }

  async function removerItem(item) {
    setSalvando(true);
    try {
      aplicar(await api.removerPeca(osId, item.id));
      toast(`${item.peca_nome} removida; estoque devolvido.`, 'success');
      setRecarga((n) => n + 1);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSalvando(false);
    }
  }

  const titulo = os ? `Ordem de Serviço #${os.id}` : 'Ordem de Serviço';
  const alterado =
    os && (Number(String(maoDeObra).replace(',', '.')) !== Number(os.valor_mao_de_obra) ||
           (diagnostico.trim() || null) !== (os.diagnostico_tecnico ?? null));

  return (
    <Modal title={titulo} onClose={onClose} wide>
      {erroCarga ? (
        <p className="error-text">{erroCarga}</p>
      ) : !os ? (
        <p className="muted">Carregando…</p>
      ) : (
        <div className="os-layout">
          <div className="stack">
            <section className="card flat">
              <div className="row between wrap">
                <div>
                  <strong>{os.cliente_nome}</strong>
                  <div className="muted">{os.cliente_telefone}</div>
                </div>
                <StatusBadge status={os.status} />
              </div>
              <dl className="details">
                <dt>Equipamento</dt>
                <dd>{os.equipamento}{os.numero_serie ? ` (${os.numero_serie})` : ''}</dd>
                <dt>Defeito relatado</dt>
                <dd>{os.defeito_relatado}</dd>
                <dt>Aberta em</dt>
                <dd>{dateTime(os.created_at)}</dd>
              </dl>

              <label className="field">
                <span>Status</span>
                <select className="input" value={os.status} disabled={salvando} onChange={(e) => mudarStatus(e.target.value)}>
                  {STATUS_ORDER.map((s) => (
                    <option key={s} value={s}>{STATUS[s].label}</option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Diagnóstico técnico</span>
                <textarea className="input" rows="3" value={diagnostico} onChange={(e) => setDiagnostico(e.target.value)} />
              </label>
              <label className="field">
                <span>Mão de obra</span>
                <input className="input" type="number" min="0" step="0.01" value={maoDeObra} onChange={(e) => setMaoDeObra(e.target.value)} />
              </label>
              <button className="btn" disabled={!alterado || salvando} onClick={salvarDados}>
                Salvar alterações
              </button>
            </section>

            <section className="card flat">
              <h3>Peças utilizadas</h3>
              {os.itens.length === 0 ? (
                <p className="muted">Nenhuma peça adicionada ainda.</p>
              ) : (
                <table className="table compact">
                  <thead>
                    <tr><th>Peça</th><th className="num">Qtd</th><th className="num">Unit.</th><th className="num">Subtotal</th><th /></tr>
                  </thead>
                  <tbody>
                    {os.itens.map((i) => (
                      <tr key={i.id}>
                        <td>{i.peca_nome}</td>
                        <td className="num">{i.quantidade_utilizada}</td>
                        <td className="num">{money(i.preco_unitario_aplicado)}</td>
                        <td className="num">{money(i.subtotal)}</td>
                        <td className="num">
                          <button className="icon-btn danger" disabled={salvando || bloqueada} onClick={() => removerItem(i)} title="Remover e devolver ao estoque" aria-label={`Remover ${i.peca_nome}`}>
                            ×
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>

          <div className="stack">
            <section className="card flat">
              <h3>Adicionar peças</h3>
              {bloqueada && <p className="muted">OS entregue: peças não podem mais ser alteradas.</p>}
              <input className="input" type="search" placeholder="Pesquisar peça pelo nome…" value={termo} onChange={(e) => setTermo(e.target.value)} />
              <ul className="parts">
                {buscando && resultados.length === 0 && <li className="muted">Buscando…</li>}
                {!buscando && resultados.length === 0 && <li className="muted">Nenhuma peça encontrada.</li>}
                {resultados.map((p) => {
                  const semEstoque = p.quantidade_estoque === 0;
                  return (
                    <li key={p.id} className="part">
                      <div className="grow">
                        <strong>{p.nome}</strong>
                        <small className={semEstoque ? 'error-text' : 'muted'}>
                          {money(p.preco_venda)} · {semEstoque ? 'sem estoque' : `${p.quantidade_estoque} em estoque`}
                        </small>
                      </div>
                      <input
                        className="input qty"
                        type="number"
                        min="1"
                        value={qtd[p.id] ?? 1}
                        onChange={(e) => setQtd((q) => ({ ...q, [p.id]: e.target.value }))}
                        aria-label={`Quantidade de ${p.nome}`}
                        disabled={bloqueada}
                      />
                      <button className="btn btn-primary" disabled={bloqueada || adicionando === p.id} onClick={() => adicionarPeca(p)}>
                        {adicionando === p.id ? '…' : 'Adicionar'}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>

            <section className="card flat summary">
              <h3>Resumo financeiro</h3>
              <div className="sum-row"><span>Mão de obra</span><span>{money(os.valor_mao_de_obra)}</span></div>
              <div className="sum-row"><span>+ Peças</span><span>{money(os.total_pecas)}</span></div>
              <div className="sum-row total"><span>= Total</span><strong>{money(os.total)}</strong></div>
            </section>
          </div>
        </div>
      )}
    </Modal>
  );
}
