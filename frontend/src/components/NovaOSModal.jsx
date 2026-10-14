import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { useDebounce } from '../useDebounce.js';
import Modal from './Modal.jsx';
import { useToast } from './Toast.jsx';

export default function NovaOSModal({ onClose, onCreated }) {
  const toast = useToast();

  // --- cliente (busca com debounce de 300 ms)
  const [buscaCliente, setBuscaCliente] = useState('');
  const buscaDebounced = useDebounce(buscaCliente, 300);
  const [clientes, setClientes] = useState([]);
  const [cliente, setCliente] = useState(null);
  const [novoCliente, setNovoCliente] = useState(null); // {nome, telefone, email} quando visível

  // --- equipamento
  const [equipamentos, setEquipamentos] = useState([]);
  const [equipamentoId, setEquipamentoId] = useState('');
  const [novoEquip, setNovoEquip] = useState(null); // {tipo, marca_modelo, numero_serie}

  // --- OS
  const [defeito, setDefeito] = useState('');
  const [maoDeObra, setMaoDeObra] = useState('0');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (cliente) return;
    const ctrl = new AbortController();
    api
      .clientes(buscaDebounced.trim(), ctrl.signal)
      .then(setClientes)
      .catch((e) => e.name !== 'AbortError' && toast(e.message, 'error'));
    return () => ctrl.abort();
  }, [buscaDebounced, cliente, toast]);

  useEffect(() => {
    if (!cliente) return;
    const ctrl = new AbortController();
    api
      .equipamentos(cliente.id, ctrl.signal)
      .then((l) => {
        setEquipamentos(l);
        setEquipamentoId(l[0] ? String(l[0].id) : '');
        if (l.length === 0) setNovoEquip({ tipo: 'Notebook', marca_modelo: '', numero_serie: '' });
      })
      .catch((e) => e.name !== 'AbortError' && toast(e.message, 'error'));
    return () => ctrl.abort();
  }, [cliente, toast]);

  async function salvarCliente(e) {
    e.preventDefault();
    try {
      const c = await api.criarCliente(novoCliente);
      setCliente(c);
      setNovoCliente(null);
      toast(`Cliente ${c.nome} cadastrado.`, 'success');
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  async function salvarEquip(e) {
    e.preventDefault();
    try {
      const eq = await api.criarEquipamento({ ...novoEquip, cliente_id: cliente.id });
      setEquipamentos((l) => [eq, ...l]);
      setEquipamentoId(String(eq.id));
      setNovoEquip(null);
      toast('Equipamento cadastrado.', 'success');
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  async function abrirOS(e) {
    e.preventDefault();
    if (!equipamentoId) {
      toast('Selecione ou cadastre um equipamento.', 'error');
      return;
    }
    setEnviando(true);
    try {
      const os = await api.criarOS({
        equipamento_id: Number(equipamentoId),
        defeito_relatado: defeito,
        valor_mao_de_obra: Number(String(maoDeObra).replace(',', '.')) || 0,
      });
      onCreated(os);
    } catch (err) {
      toast(err.message, 'error');
      setEnviando(false);
    }
  }

  const setNC = (k) => (e) => setNovoCliente((v) => ({ ...v, [k]: e.target.value }));
  const setNE = (k) => (e) => setNovoEquip((v) => ({ ...v, [k]: e.target.value }));

  return (
    <Modal title="Nova ordem de serviço" onClose={onClose}>
      <div className="stack">
        <section>
          <h3>1. Cliente</h3>
          {cliente ? (
            <div className="row between card flat">
              <div>
                <strong>{cliente.nome}</strong>
                <div className="muted">{cliente.telefone}</div>
              </div>
              <button className="btn" onClick={() => { setCliente(null); setEquipamentos([]); setNovoEquip(null); }}>
                Trocar
              </button>
            </div>
          ) : novoCliente ? (
            <form className="stack" onSubmit={salvarCliente}>
              <input className="input" placeholder="Nome" required value={novoCliente.nome} onChange={setNC('nome')} />
              <input className="input" placeholder="Telefone (ex.: +244 923 456 789)" required value={novoCliente.telefone} onChange={setNC('telefone')} />
              <input className="input" type="email" placeholder="E-mail (opcional)" value={novoCliente.email} onChange={setNC('email')} />
              <div className="row">
                <button className="btn btn-primary" type="submit">Salvar cliente</button>
                <button className="btn" type="button" onClick={() => setNovoCliente(null)}>Cancelar</button>
              </div>
            </form>
          ) : (
            <div className="stack">
              <input className="input" type="search" placeholder="Buscar cliente por nome, telefone ou e-mail…" value={buscaCliente} onChange={(e) => setBuscaCliente(e.target.value)} />
              <ul className="parts">
                {clientes.map((c) => (
                  <li key={c.id} className="part clickable" onClick={() => setCliente(c)}>
                    <div className="grow">
                      <strong>{c.nome}</strong>
                      <small className="muted">{c.telefone}</small>
                    </div>
                    <span className="btn">Selecionar</span>
                  </li>
                ))}
                {clientes.length === 0 && <li className="muted">Nenhum cliente encontrado.</li>}
              </ul>
              <button className="btn" onClick={() => setNovoCliente({ nome: buscaCliente, telefone: '', email: '' })}>
                + Novo cliente
              </button>
            </div>
          )}
        </section>

        {cliente && (
          <form className="stack" onSubmit={abrirOS}>
            <section className="stack">
              <h3>2. Equipamento</h3>
              {novoEquip ? (
                <div className="stack">
                  <input className="input" placeholder="Tipo (Notebook, Smartphone…)" required value={novoEquip.tipo} onChange={setNE('tipo')} />
                  <input className="input" placeholder="Marca / modelo" required value={novoEquip.marca_modelo} onChange={setNE('marca_modelo')} />
                  <input className="input" placeholder="Nº de série (opcional)" value={novoEquip.numero_serie} onChange={setNE('numero_serie')} />
                  <div className="row">
                    <button className="btn btn-primary" type="button" onClick={salvarEquip}>Salvar equipamento</button>
                    {equipamentos.length > 0 && <button className="btn" type="button" onClick={() => setNovoEquip(null)}>Cancelar</button>}
                  </div>
                </div>
              ) : (
                <div className="row">
                  <select className="input grow" value={equipamentoId} onChange={(e) => setEquipamentoId(e.target.value)}>
                    {equipamentos.map((eq) => (
                      <option key={eq.id} value={eq.id}>{eq.tipo} · {eq.marca_modelo}</option>
                    ))}
                  </select>
                  <button className="btn" type="button" onClick={() => setNovoEquip({ tipo: 'Notebook', marca_modelo: '', numero_serie: '' })}>
                    + Novo
                  </button>
                </div>
              )}
            </section>

            <section className="stack">
              <h3>3. Detalhes</h3>
              <label className="field">
                <span>Defeito relatado</span>
                <textarea className="input" rows="3" required minLength={3} value={defeito} onChange={(e) => setDefeito(e.target.value)} />
              </label>
              <label className="field">
                <span>Mão de obra (estimada)</span>
                <input className="input" type="number" min="0" step="0.01" value={maoDeObra} onChange={(e) => setMaoDeObra(e.target.value)} />
              </label>
            </section>

            <button className="btn btn-primary" type="submit" disabled={enviando || !!novoEquip}>
              {enviando ? 'Abrindo…' : 'Abrir OS'}
            </button>
          </form>
        )}
      </div>
    </Modal>
  );
}
