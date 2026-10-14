import { useState } from 'react';
import Dashboard from './components/Dashboard.jsx';
import OrdensServico from './components/OrdensServico.jsx';

export default function App() {
  const [aba, setAba] = useState('dashboard');
  const [statusInicial, setStatusInicial] = useState('');

  const irParaOS = (status = '') => {
    setStatusInicial(status);
    setAba('os');
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🔧</span> TechFix <b>Pro</b>
        </div>
        <nav>
          <button className={aba === 'dashboard' ? 'tab active' : 'tab'} onClick={() => setAba('dashboard')}>
            Dashboard
          </button>
          <button className={aba === 'os' ? 'tab active' : 'tab'} onClick={() => irParaOS('')}>
            Ordens de Serviço
          </button>
        </nav>
      </header>
      <main className="content">
        <h1>{aba === 'dashboard' ? 'Visão geral' : 'Ordens de Serviço'}</h1>
        {aba === 'dashboard' ? <Dashboard onOpenOS={irParaOS} /> : <OrdensServico initialStatus={statusInicial} />}
      </main>
    </div>
  );
}
