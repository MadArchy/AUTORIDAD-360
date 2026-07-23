import React from 'react';


export default function ReportTab({
  loading,
  generateReport,
  report,
  reportError,
  notify
}) {
  return (
    <>
{true && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '10px', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Reporte Semanal Generado</h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-primary" disabled={loading} onClick={generateReport}>
                Generar reporte
              </button>
              <button className="btn btn-secondary" onClick={() => { navigator.clipboard.writeText(report?.markdown_report || ''); notify('Copiado', 'success'); }}>
                Copiar Markdown
              </button>
            </div>
          </div>

          {reportError && (
            <p style={{ color: '#F59E0B', marginBottom: '12px' }}>{reportError}</p>
          )}
          {report ? (
            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '24px', borderRadius: '12px', fontFamily: 'var(--font-mono)', fontSize: '0.88rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {report.markdown_report}
            </div>
          ) : (
            <p style={{ color: 'var(--text-secondary)' }}>
              {loading ? 'Cargando reporte…' : 'No hay reporte cargado. Pulsa Generar reporte.'}
            </p>
          )}
        </section>
      )}

    </>
  );
}
