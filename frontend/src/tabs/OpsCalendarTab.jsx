import React from 'react';
import { Calendar, RefreshCw, CheckCircle2, Clock, History } from 'lucide-react';

export default function OpsCalendarTab({
  loading,
  calendarSlots,
  decisionLogs,
  onGenerateCalendar,
  onRefresh,
  onCompleteTask,
  onApproveSlot,
  onPublishFromSlot,
  onPrepareApproval,
}) {
  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Parrilla Editorial, Tareas & Semáforo de Riesgo (Fase 4)</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Gestión operativa con evaluación de semáforo de riesgo (Verde / Amarillo / Rojo) e historial de decisiones trazables.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-primary" disabled={loading} onClick={onGenerateCalendar}>
            Generar calendario
          </button>
          <button className="btn btn-secondary" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={16} /> Actualizar Operaciones
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', borderRadius: '10px', padding: '16px' }}>
          <span style={{ fontWeight: 800, color: '#10B981', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="risk-dot risk-green" /> VERDE — BAJO RIESGO
          </span>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Noticias factuales verificadas. Flujo de aprobación directo.</p>
        </div>
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)', borderRadius: '10px', padding: '16px' }}>
          <span style={{ fontWeight: 800, color: '#F59E0B', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="risk-dot risk-yellow" /> AMARILLO — REVISIÓN PREVENTIVA
          </span>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Mención a marcas registradas u organismos reguladores.</p>
        </div>
        <div style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', borderRadius: '10px', padding: '16px' }}>
          <span style={{ fontWeight: 800, color: '#EF4444', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="risk-dot risk-red" /> ROJO — REVISIÓN EXPLÍCITA
          </span>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Temas de litigios, demandas o afirmaciones sensibles.</p>
        </div>
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Calendar size={20} style={{ color: 'var(--accent-cyan)' }} /> Parrilla Editorial de la Cadencia Actual (2 Semanas)
      </h3>

      <div className="grid-cards" style={{ marginBottom: '32px' }}>
        {calendarSlots.length === 0 && (
          <div className="glass-card" style={{ padding: '24px', color: 'var(--text-secondary)' }}>
            No hay slots en el horizonte. Pulsa <strong>Generar calendario</strong> para crear la parrilla de 2 semanas.
          </div>
        )}
        {calendarSlots.map((slot) => {
          const risk = (slot.risk_level || 'yellow').toLowerCase();
          const doneStatuses = new Set(['done', 'completed']);
          const canApprove = slot.status === 'pending_approval';
          return (
            <div key={slot.id} className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span className="score-tag">{slot.channel}</span>
                <span className={`status-badge status-${risk === 'green' ? 'verified' : risk === 'yellow' ? 'pending' : 'rejected'}`}>
                  {risk.toUpperCase()}
                </span>
              </div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '8px', lineHeight: 1.4 }}>{slot.title}</h4>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                <strong>Programado:</strong>{' '}
                {slot.scheduled_at
                  ? new Date(slot.scheduled_at).toLocaleString()
                  : slot.scheduled_date
                    ? new Date(slot.scheduled_date).toLocaleDateString()
                    : '—'}
                {' '}| <strong>Formato:</strong> {(slot.format_type || '').toUpperCase()}
                {' '}| <strong>Estado:</strong> {slot.status}
                {slot.piece_id ? ` | pieza #${slot.piece_id}` : ''}
                {' '}| <strong>Estado:</strong> {slot.status}
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                <strong>Evaluación de Riesgo:</strong> {slot.risk_reason}
              </div>
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ fontSize: '0.82rem', color: '#FFF' }}>Tareas Operativas ({(slot.tasks || []).length}):</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {(slot.tasks || []).map((t) => (
                    <li key={t.id} style={{ marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span>
                        {doneStatuses.has(t.status) ? <CheckCircle2 size={14} color="#10B981" /> : <Clock size={14} color="#94A3B8" />}{' '}
                        {t.task_name} <span style={{ color: 'var(--text-muted)' }}>({t.assignee})</span>
                      </span>
                      {!doneStatuses.has(t.status) && t.task_type !== 'publish' && slot.piece_id && (
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '2px 8px', fontSize: '0.72rem' }}
                          onClick={() => onCompleteTask(t.id)}
                        >
                          Completar
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
              <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {slot.status === 'published' ? (
                  <span className="status-badge status-verified" style={{ width: '100%', textAlign: 'center', display: 'block' }}>
                    PUBLICADO
                  </span>
                ) : slot.status === 'scheduled' ? (
                  <>
                    <span className="status-badge status-verified" style={{ width: '100%', textAlign: 'center', display: 'block' }}>
                      PROGRAMADO
                    </span>
                    {slot.piece_id && onPublishFromSlot && (
                      <button
                        className="btn btn-secondary"
                        style={{ width: '100%', padding: '8px', fontSize: '0.8rem' }}
                        onClick={() => onPublishFromSlot(slot.id)}
                      >
                        Regenerar paquete multi-canal
                      </button>
                    )}
                  </>
                ) : slot.status === 'approved' ? (
                  <>
                    <span className="status-badge status-pending" style={{ width: '100%', textAlign: 'center', display: 'block' }}>
                      APROBADO
                    </span>
                    {slot.piece_id && onPublishFromSlot && (
                      <button
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '8px', fontSize: '0.85rem' }}
                        onClick={() => onPublishFromSlot(slot.id)}
                      >
                        Crear paquete multi-canal
                      </button>
                    )}
                  </>
                ) : canApprove ? (
                  <>
                    <button
                      className="btn btn-success"
                      style={{ width: '100%', padding: '8px', fontSize: '0.85rem' }}
                      onClick={() => onApproveSlot(slot.id, false)}
                    >
                      <CheckCircle2 size={14} /> Aprobar para Publicación
                    </button>
                    {risk === 'red' && (
                      <button
                        className="btn btn-secondary"
                        style={{ width: '100%', padding: '8px', fontSize: '0.8rem' }}
                        onClick={() => onApproveSlot(slot.id, true)}
                      >
                        Aprobar con override de riesgo
                      </button>
                    )}
                  </>
                ) : slot.piece_id ? (
                  <button
                    className="btn btn-primary"
                    style={{ width: '100%', padding: '8px', fontSize: '0.85rem' }}
                    onClick={() => onPrepareApproval(slot.id)}
                  >
                    Listo para aprobación
                  </button>
                ) : (
                  <span style={{ display: 'block', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Adjunta una pieza multi-formato antes de aprobar
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <History size={20} style={{ color: 'var(--accent-purple)' }} /> Historial de Decisiones & Auditoría de Aprobaciones
      </h3>

      <div className="glass-card" style={{ padding: '20px' }}>
        {decisionLogs.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '10px' }}>FECHA / HORA</th>
                <th style={{ padding: '10px' }}>ACTOR</th>
                <th style={{ padding: '10px' }}>ACCIÓN</th>
                <th style={{ padding: '10px' }}>ENTIDAD</th>
                <th style={{ padding: '10px' }}>RAZÓN AUDITADA</th>
              </tr>
            </thead>
            <tbody>
              {decisionLogs.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>{new Date(log.created_at).toLocaleString()}</td>
                  <td style={{ padding: '10px', fontWeight: 700 }}>{log.actor}</td>
                  <td style={{ padding: '10px' }}>
                    <span className="status-badge status-verified">{log.action.toUpperCase()}</span>
                  </td>
                  <td style={{ padding: '10px' }}>{log.entity_type} #{log.entity_id}</td>
                  <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{log.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--text-secondary)' }}>No hay decisiones registradas aún en el historial.</p>
        )}
      </div>
    </section>
  );
}
