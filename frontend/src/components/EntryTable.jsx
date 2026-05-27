// src/components/EntryTable.jsx
import { useEffect, useState } from 'react';
import { getEntries, approveEntry, rejectEntry, flagEntry } from '../api/client';
import StatusBadge from './StatusBadge';

export default function EntryTable({ onSelectEntry }) {
  const [entries, setEntries]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [filters, setFilters]   = useState({ status: '', source: '', scope: '' });
  const [actionNote, setActionNote] = useState('');
  const [acting, setActing]     = useState(null);


  useEffect(() => {
    const active = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    setLoading(true);
    getEntries(active)
      .then(res => setEntries(res.data.entries))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, [filters]);

  const handleAction = async (id, action) => {
    setActing(id + action);
    try {
      if (action === 'approve') await approveEntry(id, actionNote);
      if (action === 'reject')  await rejectEntry(id, actionNote);
      if (action === 'flag')    await flagEntry(id, actionNote);
      await load();
    } catch (e) {
      alert(e.response?.data?.error || 'Action failed');
    } finally {
      setActing(null);
      setActionNote('');
    }
  };

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111' }}>
          Entries <span style={{ fontSize: 14, color: '#6b7280', fontWeight: 400 }}>({entries.length})</span>
        </h2>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 10 }}>
          {[
            { key: 'status', options: ['', 'PENDING', 'APPROVED', 'REJECTED', 'FLAGGED'], label: 'Status' },
            { key: 'source', options: ['', 'SAP_FUEL', 'UTILITY_ELECTRICITY', 'TRAVEL'], label: 'Source' },
            { key: 'scope',  options: ['', 'SCOPE_1', 'SCOPE_2', 'SCOPE_3'], label: 'Scope' },
          ].map(f => (
            <select
              key={f.key}
              value={filters[f.key]}
              onChange={e => setFilters(p => ({ ...p, [f.key]: e.target.value }))}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13 }}
            >
              <option value="">All {f.label}s</option>
              {f.options.filter(Boolean).map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
            </select>
          ))}
          <button
            onClick={() => {
              const active = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
              setLoading(true);
              getEntries(active)
                .then(res => setEntries(res.data.entries))
                .catch(e => console.error(e))
                .finally(() => setLoading(false));
            }}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#f9fafb', cursor: 'pointer', fontSize: 13 }}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>Loading entries...</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f3f4f6', background: '#f9fafb' }}>
                {['Source', 'Description', 'Scope', 'Value', 'CO₂e (kg)', 'Status', 'Flagged', 'Actions'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr
                  key={e.id}
                  style={{
                    borderBottom: '1px solid #f3f4f6',
                    background: e.is_flagged_auto ? '#fffbeb' : '#fff',
                  }}
                >
                  <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', background: '#f3f4f6', padding: '2px 6px', borderRadius: 4 }}>
                      {e.source_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td
                    style={{ padding: '10px 12px', color: '#1e40af', cursor: 'pointer', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    onClick={() => onSelectEntry && onSelectEntry(e.id)}
                    title={e.description}
                  >
                    {e.description}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 11, fontWeight: 700, color: '#7c3aed' }}>{e.scope}</td>
                  <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                    {parseFloat(e.normalized_value).toFixed(2)} {e.normalized_unit}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, whiteSpace: 'nowrap' }}>
                    {parseFloat(e.co2e_kg).toFixed(2)}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <StatusBadge status={e.review_status} />
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {e.is_flagged_auto && (
                      <span title={e.flag_reason} style={{ color: '#dc2626', fontSize: 16, cursor: 'help' }}>⚠</span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                    {!e.is_locked ? (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          disabled={!!acting}
                          onClick={() => handleAction(e.id, 'approve')}
                          style={{ padding: '4px 10px', borderRadius: 5, border: 'none', background: '#059669', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
                        >
                          {acting === e.id + 'approve' ? '...' : '✓ Approve'}
                        </button>
                        <button
                          disabled={!!acting}
                          onClick={() => handleAction(e.id, 'flag')}
                          style={{ padding: '4px 10px', borderRadius: 5, border: 'none', background: '#7c3aed', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
                        >
                          {acting === e.id + 'flag' ? '...' : '⚑ Flag'}
                        </button>
                        <button
                          disabled={!!acting}
                          onClick={() => handleAction(e.id, 'reject')}
                          style={{ padding: '4px 10px', borderRadius: 5, border: 'none', background: '#dc2626', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
                        >
                          {acting === e.id + 'reject' ? '...' : '✗ Reject'}
                        </button>
                      </div>
                    ) : (
                      <span style={{ fontSize: 12, color: '#6b7280', fontStyle: 'italic' }}>🔒 Locked</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}