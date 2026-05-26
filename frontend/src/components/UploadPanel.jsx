// src/components/UploadPanel.jsx
import { useState } from 'react';
import { uploadFile } from '../api/client';

const SOURCES = [
  { value: 'SAP_FUEL',            label: 'SAP Fuel & Procurement',  desc: 'CSV flat file export from SAP' },
  { value: 'UTILITY_ELECTRICITY', label: 'Utility Electricity',     desc: 'Portal CSV export from utility provider' },
  { value: 'TRAVEL',              label: 'Corporate Travel',        desc: 'Concur/Navan CSV export' },
];

export default function UploadPanel({ onUploadSuccess }) {
  const [sourceType, setSourceType] = useState('SAP_FUEL');
  const [file, setFile]             = useState(null);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await uploadFile(file, sourceType);
      setResult(res.data.summary);
      setFile(null);
      if (onUploadSuccess) onUploadSuccess();
    } catch (e) {
      setError(e.response?.data?.error || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, color: '#111' }}>
        Upload Data File
      </h2>

      {/* Source selector */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        {SOURCES.map(s => (
          <div
            key={s.value}
            onClick={() => setSourceType(s.value)}
            style={{
              flex: 1, padding: '12px 16px', borderRadius: 8, cursor: 'pointer',
              border: sourceType === s.value ? '2px solid #059669' : '2px solid #e5e7eb',
              background: sourceType === s.value ? '#ecfdf5' : '#f9fafb',
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13, color: '#111' }}>{s.label}</div>
            <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{s.desc}</div>
          </div>
        ))}
      </div>

      {/* File input */}
      <div
        style={{
          border: '2px dashed #d1d5db', borderRadius: 8, padding: 32,
          textAlign: 'center', background: '#f9fafb', marginBottom: 16,
        }}
      >
        <input
          type="file"
          accept=".csv"
          onChange={e => setFile(e.target.files[0])}
          style={{ display: 'block', margin: '0 auto' }}
        />
        {file && (
          <div style={{ marginTop: 8, fontSize: 13, color: '#059669', fontWeight: 600 }}>
            ✓ {file.name}
          </div>
        )}
      </div>

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!file || loading}
        style={{
          width: '100%', padding: '12px 0', borderRadius: 8, border: 'none',
          background: (!file || loading) ? '#d1d5db' : '#059669',
          color: '#fff', fontWeight: 700, fontSize: 15, cursor: (!file || loading) ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? 'Processing...' : 'Upload & Ingest'}
      </button>

      {/* Result */}
      {result && (
        <div style={{ marginTop: 16, padding: 16, background: '#ecfdf5', borderRadius: 8 }}>
          <div style={{ fontWeight: 700, color: '#065f46', marginBottom: 8 }}>✓ File processed successfully</div>
          <div style={{ display: 'flex', gap: 24, fontSize: 13 }}>
            <span>Total: <strong>{result.total}</strong></span>
            <span style={{ color: '#059669' }}>Success: <strong>{result.success}</strong></span>
            <span style={{ color: '#dc2626' }}>Failed: <strong>{result.failed}</strong></span>
            <span style={{ color: '#7c3aed' }}>Suspicious: <strong>{result.suspicious}</strong></span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ marginTop: 16, padding: 16, background: '#fee2e2', borderRadius: 8, color: '#991b1b', fontWeight: 600 }}>
          ✗ {error}
        </div>
      )}
    </div>
  );
}