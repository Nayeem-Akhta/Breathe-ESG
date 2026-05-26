// src/components/Dashboard.jsx
import { useEffect, useState } from 'react';
import { getDashboard } from '../api/client';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = ['#059669', '#dc2626', '#7c3aed', '#f59e0b'];

export default function Dashboard() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const res = await getDashboard();
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div style={{ padding: 24, color: '#6b7280' }}>Loading dashboard...</div>;
  if (!data)   return <div style={{ padding: 24, color: '#dc2626' }}>Failed to load dashboard</div>;

  const { review_summary, co2e_by_scope, recent_batches } = data;

  const statusData = [
    { name: 'Approved', value: review_summary.approved },
    { name: 'Rejected', value: review_summary.rejected },
    { name: 'Flagged',  value: review_summary.flagged  },
    { name: 'Pending',  value: review_summary.pending  },
  ].filter(d => d.value > 0);

  const scopeData = [
    { name: 'Scope 1', value: parseFloat(co2e_by_scope.scope_1_kg) },
    { name: 'Scope 2', value: parseFloat(co2e_by_scope.scope_2_kg) },
    { name: 'Scope 3', value: parseFloat(co2e_by_scope.scope_3_kg) },
  ].filter(d => d.value > 0);

  const cards = [
    { label: 'Pending Review', value: review_summary.pending,    color: '#f59e0b', bg: '#fffbeb' },
    { label: 'Approved',       value: review_summary.approved,   color: '#059669', bg: '#ecfdf5' },
    { label: 'Flagged',        value: review_summary.flagged,    color: '#7c3aed', bg: '#ede9fe' },
    { label: 'Suspicious',     value: review_summary.suspicious, color: '#dc2626', bg: '#fee2e2' },
  ];

  const totalCo2e = parseFloat(co2e_by_scope.total_kg).toFixed(1);

  return (
    <div>
      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {cards.map(c => (
          <div key={c.label} style={{
            background: c.bg, borderRadius: 12, padding: '20px 24px',
            borderLeft: `4px solid ${c.color}`,
          }}>
            <div style={{ fontSize: 13, color: '#6b7280', fontWeight: 600 }}>{c.label}</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: c.color, marginTop: 4 }}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* CO2e total */}
      <div style={{
        background: '#0f172a', borderRadius: 12, padding: '24px 32px',
        marginBottom: 24, color: '#fff',
      }}>
        <div style={{ fontSize: 13, color: '#94a3b8', fontWeight: 600 }}>TOTAL APPROVED CO₂e</div>
        <div style={{ fontSize: 48, fontWeight: 800, color: '#34d399', margin: '8px 0' }}>
          {totalCo2e} <span style={{ fontSize: 20, color: '#94a3b8' }}>kg</span>
        </div>
        <div style={{ display: 'flex', gap: 32, fontSize: 13, color: '#94a3b8' }}>
          <span>Scope 1: <strong style={{ color: '#fff' }}>{parseFloat(co2e_by_scope.scope_1_kg).toFixed(1)} kg</strong></span>
          <span>Scope 2: <strong style={{ color: '#fff' }}>{parseFloat(co2e_by_scope.scope_2_kg).toFixed(1)} kg</strong></span>
          <span>Scope 3: <strong style={{ color: '#fff' }}>{parseFloat(co2e_by_scope.scope_3_kg).toFixed(1)} kg</strong></span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {/* Review status chart */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#111' }}>Review Status</h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#6b7280', fontSize: 13, textAlign: 'center', paddingTop: 60 }}>No data yet</div>
          )}
        </div>

        {/* CO2e by scope chart */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#111' }}>CO₂e by Scope (Approved)</h3>
          {scopeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={scopeData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value.toFixed(0)}kg`}>
                  {scopeData.map((_, i) => <Cell key={i} fill={['#3b82f6', '#f59e0b', '#8b5cf6'][i]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#6b7280', fontSize: 13, textAlign: 'center', paddingTop: 60 }}>Approve entries to see CO₂e breakdown</div>
          )}
        </div>
      </div>

      {/* Recent batches */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#111' }}>Recent Ingestion Batches</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #f3f4f6' }}>
              {['Source', 'File', 'Status', 'Total', 'Success', 'Failed', 'Uploaded'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#6b7280', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent_batches.map(b => (
              <tr key={b.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600 }}>{b.source_type.replace('_', ' ')}</td>
                <td style={{ padding: '10px 12px', color: '#6b7280' }}>{b.file_name}</td>
                <td style={{ padding: '10px 12px' }}>
                  <span style={{ background: '#d1fae5', color: '#065f46', padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 700 }}>
                    {b.status}
                  </span>
                </td>
                <td style={{ padding: '10px 12px' }}>{b.total_rows}</td>
                <td style={{ padding: '10px 12px', color: '#059669', fontWeight: 600 }}>{b.successful_rows}</td>
                <td style={{ padding: '10px 12px', color: b.failed_rows > 0 ? '#dc2626' : '#6b7280', fontWeight: b.failed_rows > 0 ? 700 : 400 }}>{b.failed_rows}</td>
                <td style={{ padding: '10px 12px', color: '#6b7280' }}>{new Date(b.uploaded_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}