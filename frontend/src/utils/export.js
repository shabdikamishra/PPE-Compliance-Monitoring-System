export function exportToCSV(violations, filename = 'violations_report.csv') {
  const headers = [
    'ID', 'Camera', 'Missing PPE', 'Detected PPE',
    'Confidence', 'Timestamp', 'Resolved'
  ];

  const rows = violations.map(v => [
    v.id,
    v.camera_id,
    (v.missing_ppe  || []).join(' | '),
    (v.detected_ppe || []).join(' | '),
    v.confidence?.toFixed(2) || '0.00',
    new Date(v.timestamp).toLocaleString('en-IN'),
    v.resolved ? 'Yes' : 'No'
  ]);

  const csvContent = [headers, ...rows]
    .map(row => row.map(cell => `"${cell}"`).join(','))
    .join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href  = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}