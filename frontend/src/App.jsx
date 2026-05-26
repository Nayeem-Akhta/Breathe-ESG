// src/App.jsx
import { useState } from 'react';
import Dashboard from './components/Dashboard';
import EntryTable from './components/EntryTable';
import UploadPanel from './components/UploadPanel';
import EntryDetail from './components/EntryDetail';

const NAV = ['Dashboard', 'Review Entries', 'Upload Data'];

export default function App() {
  const [tab, setTab]               = useState('Dashboard');
  const [selectedEntry, setSelected] = useState(null);
  const [refreshKey, setRefreshKey]  = useState(0);

  const refresh = () => setRefreshKey(k => k + 1);

  return (
    <div style={{ minHeight: '100vh', background: '#f1f5f9', fontFamily: 'Inter, system-ui, sans-serif' }}>

      {/* Top nav */}
      <nav style={{
        background: '#0f172a', padding: '0 32px',
        display: 'flex', alignItems: 'center', gap: 32, height: 60,
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}>
        <div style={{ color: '#34d399', fontWeight: 800, fontSize: 18, letterSpacing: -0.5 }}>
          🌿 Breathe ESG
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {NAV.map(n => (
            <button
              key={n}
              onClick={() => setTab(n)}
              style={{
                padding: '6px 16px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: tab === n ? '#1e293b' : 'transparent',
                color: tab === n ? '#34d399' : '#94a3b8',
                fontWeight: tab === n ? 700 : 400,
                fontSize: 14,
              }}
            >
              {n}
            </button>
          ))}
        </div>
      </nav>

      {/* Page content */}
      <main style={{ padding: '32px', maxWidth: 1200, margin: '0 auto' }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', marginBottom: 24 }}>
          {tab === 'Dashboard'       && '📊 Dashboard'}
          {tab === 'Review Entries'  && '🔍 Review Entries'}
          {tab === 'Upload Data'     && '📤 Upload Data'}
        </h1>

        {tab === 'Dashboard'      && <Dashboard key={refreshKey} />}
        {tab === 'Review Entries' && (
          <EntryTable
            key={refreshKey}
            onSelectEntry={setSelected}
          />
        )}
        {tab === 'Upload Data' && (
          <UploadPanel onUploadSuccess={() => { refresh(); setTab('Review Entries'); }} />
        )}
      </main>

      {/* Entry detail modal */}
      {selectedEntry && (
        <EntryDetail
          entryId={selectedEntry}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}