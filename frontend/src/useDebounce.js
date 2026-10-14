import { useEffect, useState } from 'react';

/** Devolve `value` somente após `delay` ms sem mudanças (padrão 300 ms). */
export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
