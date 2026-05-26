// src/components/StatusBadge.jsx

export default function StatusBadge({ status }) {
    const config = {
      PENDING:  { background: '#fef3c7', color: '#92400e' },
      APPROVED: { background: '#d1fae5', color: '#065f46' },
      REJECTED: { background: '#fee2e2', color: '#991b1b' },
      FLAGGED:  { background: '#ede9fe', color: '#5b21b6' },
    };
  
    const style = config[status] || { background: '#f3f4f6', color: '#374151' };
  
    return (
      <span style={{
        padding: '2px 10px',
        borderRadius: '999px',
        fontSize: '12px',
        fontWeight: 600,
        background: style.background,
        color: style.color,
      }}>
        {status}
      </span>
    );
  }