// src/components/EntryDetail.jsx
import { useEffect, useState } from 'react';
import { getEntry } from '../api/client';
import StatusBadge from './StatusBadge';

export default function EntryDetail({ entryId, onClose }) {
  const [entry, setEntry]   = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!entryId) return;
    setLoading(true);
    getEntry(entryId)
      .then(res => setEntry(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [entryId]);

  if (!entryId) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: '#fff', borderRadius: 16, padding: 32, width: 640,
        maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111' }}>Entry Detail</h2>
          <button onClick={onClose} style={{ border: 'none', background: 'none', fontSize: 24, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>Loading...</div>
        ) : entry ? (
          <>
            {/* Main details */}
            <div style={{ background: '#f9fafb', borderRadius: 8, padding: 16, marginBottom: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 13 }}>
                {[
                  ['Description',   entry.description],
                  ['Category',      entry.category],
                  ['Source',        entry.source_type],
                  ['Scope',         entry.scope],
                  ['Raw Value',     `${entry.raw_value} ${entry.raw_unit}`],
                  ['Normalized',    `${entry.normalized_value} ${entry.normalized_unit}`],
                  ['Emission Factor', `${entry.emission_factor} kg CO₂e/${entry.normalized_unit}`],
                  ['Factor Source', entry.emission_factor_source],
                  ['Activity Date', entry.activity_date || '—'],
                  ['CO₂e',         `${parseFloat(entry.co2e_kg).toFixed(4)} kg`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div style={{ color: '#6b7280', fontWeight: 600, fontSize: 11, marginBottom: 2 }}>{label}</div>
                    <div style={{ color: '#111', fontWeight: 500 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Status + flags */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 20, alignItems: 'center' }}>
              <StatusBadge status={entry.review_status} />
              {entry.is_locked && <span style={{ fontSize: 12, color: '#6b7280' }}>🔒 Locked for audit</span>}
              {entry.is_flagged_auto && (
                <span style={{ fontSize: 12, color: '#dc2626', background: '#fee2e2', padding: '2px 8px', borderRadius: 6 }}>
                  ⚠ {entry.flag_reason}
                </span>
              )}
            </div>

            {/* Audit trail */}
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#111', marginBottom: 12 }}>Audit Trail</h3>
              {entry.audit_trail?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {entry.audit_trail.map((log, i) => (
                    <div key={i} style={{
                      padding: 12, borderRadius: 8, background: '#f9fafb',
                      borderLeft: '3px solid #059669', fontSize: 12,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <strong style={{ color: '#059669' }}>{log.action}</strong>
                        <span style={{ color: '#6b7280' }}>{new Date(log.timestamp).toLocaleString()}</span>
                      </div>
                      <div style={{ color: '#374151' }}>By: {log.user || 'System'}</div>
                      {log.after_value?.note && (
                        <div style={{ color: '#6b7280', marginTop: 4, fontStyle: 'italic' }}>
                          Note: {log.after_value.note}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: '#6b7280', fontSize: 13 }}>No audit events yet</div>
              )}
            </div>
          </>
        ) : (
          <div style={{ color: '#dc2626' }}>Entry not found</div>
        )}
      </div>
    </div>
  );
}