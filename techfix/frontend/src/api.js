const BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function extractMessage(data, status) {
  const d = data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d
      .map((e) => {
        const campo = (e.loc || []).slice(1).join('.');
        return campo ? `${campo}: ${e.msg}` : e.msg;
      })
      .join('; ');
  }
  if (d && typeof d === 'object') {
    const candidates = [d.message, d.error, d.msg, d.detail, d.non_field_errors];
    for (const candidate of candidates) {
      if (typeof candidate === 'string' && candidate.trim()) return candidate;
      if (Array.isArray(candidate)) {
        const joined = candidate
          .map((item) => (typeof item === 'string' ? item : item?.message || item?.msg || JSON.stringify(item)))
          .filter(Boolean)
          .join('; ');
        if (joined) return joined;
      }
    }
    return JSON.stringify(d);
  }
  return `Erro inesperado (${status}).`;
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new ApiError('Não foi possível conectar ao servidor. Verifique se o backend está em execução.', 0);
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* corpo vazio ou não-JSON */
  }
  if (!res.ok) throw new ApiError(extractMessage(data, res.status), res.status);
  return data;
}

const qs = (params) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, v);
  });
  const s = p.toString();
  return s ? `?${s}` : '';
};

export const api = {
  dashboard: (signal) => request('/api/dashboard', { signal }),

  clientes: (q, signal) => request(`/api/clientes${qs({ q, limit: 8 })}`, { signal }),
  criarCliente: (body) => request('/api/clientes', { method: 'POST', body }),

  equipamentos: (clienteId, signal) => request(`/api/equipamentos${qs({ cliente_id: clienteId })}`, { signal }),
  criarEquipamento: (body) => request('/api/equipamentos', { method: 'POST', body }),

  pecas: (q, signal) => request(`/api/pecas${qs({ q, limit: 8 })}`, { signal }),

  listarOS: ({ status, q }, signal) => request(`/api/ordens-servico${qs({ status, q })}`, { signal }),
  obterOS: (id, signal) => request(`/api/ordens-servico/${id}`, { signal }),
  criarOS: (body) => request('/api/ordens-servico', { method: 'POST', body }),
  editarOS: (id, body) => request(`/api/ordens-servico/${id}`, { method: 'PATCH', body }),
  atualizarStatus: (id, status) => request(`/api/ordens-servico/${id}/status`, { method: 'PATCH', body: { status } }),
  adicionarPeca: (id, body) => request(`/api/ordens-servico/${id}/pecas`, { method: 'POST', body }),
  removerPeca: (id, itemId) => request(`/api/ordens-servico/${id}/pecas/${itemId}`, { method: 'DELETE' }),
};
