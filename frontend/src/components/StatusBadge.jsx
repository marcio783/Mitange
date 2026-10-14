import { STATUS } from '../utils.js';

export default function StatusBadge({ status }) {
  const s = STATUS[status] ?? { label: status, cls: 'entregue' };
  return <span className={`badge badge-${s.cls}`}>{s.label}</span>;
}
