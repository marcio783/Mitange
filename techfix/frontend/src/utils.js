export const STATUS = {
  PENDENTE: { label: 'Pendente', cls: 'pendente' }, // laranja
  EM_ANALISE: { label: 'Em análise', cls: 'analise' }, // azul
  AGUARDANDO_PECA: { label: 'Aguardando peça', cls: 'aguardando' }, // roxo
  CONCLUIDO: { label: 'Concluído', cls: 'concluido' }, // verde
  ENTREGUE: { label: 'Entregue', cls: 'entregue' }, // cinza
};

export const STATUS_ORDER = Object.keys(STATUS);

// Altere aqui para trocar a moeda exibida (ex.: BRL / pt-BR, EUR / pt-PT).
const CURRENCY = { locale: 'pt-AO', currency: 'AOA' };

export const money = (v) =>
  new Intl.NumberFormat(CURRENCY.locale, { style: 'currency', currency: CURRENCY.currency }).format(Number(v || 0));

export const dateTime = (iso) =>
  iso ? new Date(iso).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' }) : '—';
