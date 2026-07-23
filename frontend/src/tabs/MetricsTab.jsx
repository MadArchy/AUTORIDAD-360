import React from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  PieChart,
  Send,
  Sliders,
  Sparkles,
  Target,
  TrendingUp,
  UserPlus,
  XCircle,
} from 'lucide-react';

export default function MetricsTab({
  dashboard,
  leads,
  leadFilter,
  setLeadFilter,
  updateLeadStatus,
  newLead,
  setNewLead,
  createLead,
  recommendations,
  generateRecommendation,
  decideRecommendation,
  loading,
  profile,
  goToTab,
}) {
  return (
    <>
{true && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>Resultados</span>
            <button type="button" className="btn btn-secondary" onClick={() => goToTab?.('hoy')}>
              Ver Hoy
            </button>
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <TrendingUp size={22} style={{ color: '#10B981' }} /> Resultados y leads
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            Herramienta avanzada: leads y aprendizaje del contenido.
          </p>

          {/* Dashboard KPIs */}
          {dashboard && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '28px' }}>
              <div className="glass-card" style={{ padding: '20px', textAlign: 'center', borderTop: '3px solid #10B981' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#10B981' }}>{dashboard.total_articles ?? 0}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Artículos</div>
              </div>
              <div className="glass-card" style={{ padding: '20px', textAlign: 'center', borderTop: '3px solid #06B6D4' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#06B6D4' }}>{dashboard.total_content_pieces ?? 0}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Piezas Generadas</div>
              </div>
              <div className="glass-card" style={{ padding: '20px', textAlign: 'center', borderTop: '3px solid #8B5CF6' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#8B5CF6' }}>{dashboard.total_leads ?? 0}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Leads</div>
              </div>
              <div className="glass-card" style={{ padding: '20px', textAlign: 'center', borderTop: '3px solid #F59E0B' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#F59E0B' }}>{dashboard.qualified_leads ?? 0}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Leads Cualificados</div>
              </div>
              <div className="glass-card" style={{ padding: '20px', textAlign: 'center', borderTop: '3px solid #EF4444' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#EF4444' }}>{dashboard.converted_leads ?? 0}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Convertidos</div>
              </div>
              <div className="glass-card" style={{ padding: '20px', textAlign: 'center', borderTop: '3px solid #EC4899' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#EC4899' }}>
                  {dashboard.conversion_rate_pct != null
                    ? `${Number(dashboard.conversion_rate_pct).toFixed(1)}%`
                    : '—'}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tasa Conversión</div>
              </div>
            </div>
          )}

          {/* Pillar breakdown */}
          {dashboard?.pillar_breakdown && dashboard.pillar_breakdown.length > 0 && (
            <div style={{ marginBottom: '28px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <PieChart size={18} style={{ color: '#8B5CF6' }} /> Desglose por Pilar
              </h3>
              <div style={{ overflowX: 'auto', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'rgba(16,185,129,0.12)' }}>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Pilar</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Piezas</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Leads</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Cualificados</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Engagement</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.pillar_breakdown.map((p, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px 16px', fontWeight: 600 }}>{p.pillar_name || p.pillar_slug}</td>
                        <td style={{ padding: '10px 16px' }}>{p.pieces ?? 0}</td>
                        <td style={{ padding: '10px 16px' }}>{p.leads ?? 0}</td>
                        <td style={{ padding: '10px 16px', color: '#10B981', fontWeight: 700 }}>{p.qualified ?? 0}</td>
                        <td style={{ padding: '10px 16px' }}>{p.total_engagement ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Leads Pipeline */}
          <div style={{ marginBottom: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Target size={18} style={{ color: '#F59E0B' }} /> Pipeline de Leads ({leads.length})
              </h3>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {['', 'new', 'contacted', 'qualified', 'converted', 'lost'].map(s => (
                  <button key={s}
                    className={`btn ${leadFilter === s ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setLeadFilter(s)}
                    style={{ fontSize: '0.75rem', padding: '5px 12px' }}
                  >
                    {s || 'Todos'}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ overflowX: 'auto', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', maxHeight: '360px', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-card)' }}>
                  <tr style={{ background: 'rgba(245,158,11,0.12)' }}>
                    <th style={{ padding: '10px 14px', fontWeight: 600 }}>Contacto</th>
                    <th style={{ padding: '10px 14px', fontWeight: 600 }}>Empresa</th>
                    <th style={{ padding: '10px 14px', fontWeight: 600 }}>Canal</th>
                    <th style={{ padding: '10px 14px', fontWeight: 600 }}>Estado</th>
                    <th style={{ padding: '10px 14px', fontWeight: 600 }}>Fecha</th>
                    <th style={{ padding: '10px 14px', fontWeight: 600 }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.filter(l => !leadFilter || l.status === leadFilter).map(l => (
                    <tr key={l.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 14px' }}>
                        <div style={{ fontWeight: 600 }}>{l.contact_name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{l.contact_email || '—'}</div>
                      </td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>{l.contact_company || '—'}</td>
                      <td style={{ padding: '8px 14px' }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: '4px', fontSize: '0.73rem', fontWeight: 600,
                          background: l.source_channel === 'linkedin' ? 'rgba(6,182,212,0.15)' : 'rgba(139,92,246,0.15)',
                          color: l.source_channel === 'linkedin' ? '#06B6D4' : '#A78BFA',
                        }}>{l.source_channel}</span>
                      </td>
                      <td style={{ padding: '8px 14px' }}>
                        <span style={{
                          padding: '3px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700,
                          background: l.status === 'converted' ? 'rgba(16,185,129,0.2)' :
                                     l.status === 'qualified' ? 'rgba(245,158,11,0.2)' :
                                     l.status === 'lost' ? 'rgba(239,68,68,0.2)' :
                                     'rgba(99,102,241,0.15)',
                          color: l.status === 'converted' ? '#10B981' :
                                 l.status === 'qualified' ? '#F59E0B' :
                                 l.status === 'lost' ? '#EF4444' :
                                 '#818CF8',
                        }}>{l.status}{l.is_qualified ? ' ✓' : ''}</span>
                      </td>
                      <td style={{ padding: '8px 14px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {l.created_at ? new Date(l.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ padding: '8px 14px' }}>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {l.status === 'new' && (
                            <button className="btn btn-secondary" style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                              onClick={() => updateLeadStatus(l.id, 'contacted')}>Contactar</button>
                          )}
                          {(l.status === 'new' || l.status === 'contacted') && (
                            <button className="btn btn-primary" style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                              onClick={() => updateLeadStatus(l.id, 'qualified')}>Cualificar</button>
                          )}
                          {l.status === 'qualified' && (
                            <button className="btn btn-primary" style={{ fontSize: '0.7rem', padding: '3px 8px', background: '#10B981' }}
                              onClick={() => updateLeadStatus(l.id, 'converted')}>Convertir</button>
                          )}
                          {l.status !== 'lost' && l.status !== 'converted' && (
                            <button className="btn btn-secondary" style={{ fontSize: '0.7rem', padding: '3px 8px', color: '#EF4444' }}
                              onClick={() => updateLeadStatus(l.id, 'lost')}>Perdido</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {leads.filter(l => !leadFilter || l.status === leadFilter).length === 0 && (
                    <tr><td colSpan={6} style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>No hay leads {leadFilter ? `con estado "${leadFilter}"` : 'registrados'}</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Create Lead Form */}
            <div className="glass-card" style={{ padding: '20px', marginTop: '16px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <UserPlus size={16} style={{ color: '#F59E0B' }} /> Registrar Nuevo Lead
              </h4>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <input type="text" placeholder="Nombre del contacto *"
                  value={newLead.contact_name} onChange={e => setNewLead({...newLead, contact_name: e.target.value})}
                  style={{ flex: 1, minWidth: '160px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input type="email" placeholder="Email"
                  value={newLead.contact_email} onChange={e => setNewLead({...newLead, contact_email: e.target.value})}
                  style={{ flex: 1, minWidth: '160px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input type="text" placeholder="Empresa"
                  value={newLead.contact_company} onChange={e => setNewLead({...newLead, contact_company: e.target.value})}
                  style={{ flex: 1, minWidth: '140px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <select
                  value={newLead.source_channel} onChange={e => setNewLead({...newLead, source_channel: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                >
                  <option value="linkedin">LinkedIn</option>
                  <option value="newsletter">Newsletter</option>
                  <option value="blog">Blog</option>
                  <option value="referral">Referido</option>
                  <option value="other">Otro</option>
                </select>
                <select
                  value={newLead.pillar_id}
                  onChange={(e) => setNewLead({ ...newLead, pillar_id: e.target.value })}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                >
                  <option value="">Pilar (opcional)</option>
                  {(profile?.pillars || []).map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                <input type="text" placeholder="utm_campaign"
                  value={newLead.utm_campaign || ''} onChange={e => setNewLead({...newLead, utm_campaign: e.target.value})}
                  style={{ flex: 1, minWidth: '120px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input type="text" placeholder="utm_source"
                  value={newLead.utm_source || ''} onChange={e => setNewLead({...newLead, utm_source: e.target.value})}
                  style={{ flex: 1, minWidth: '100px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input type="number" placeholder="piece_id"
                  value={newLead.piece_id || ''} onChange={e => setNewLead({...newLead, piece_id: e.target.value})}
                  style={{ width: '110px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <button className="btn btn-primary" onClick={createLead} style={{ whiteSpace: 'nowrap' }}>
                  <Send size={16} /> Registrar Lead
                </button>
              </div>
            </div>
          </div>

          {/* Percentage Recommendations */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={18} style={{ color: '#EC4899' }} /> Recomendaciones de Ajuste de Porcentaje
              </h3>
              <button className="btn btn-secondary" onClick={generateRecommendation} disabled={loading}>
                <Sparkles size={16} /> Generar Recomendación
              </button>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
              Las recomendaciones se generan según leads cualificados, no engagement superficial. Se requieren al menos 3 leads cualificados en el periodo para generar una sugerencia.
            </p>

            {recommendations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {recommendations.map(rec => (
                  <div key={rec.id} className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #EC4899' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <div>
                        <div style={{ fontWeight: 700, marginBottom: '4px' }}>Recomendación #{rec.id}</div>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                          {rec.created_at ? new Date(rec.created_at).toLocaleString() : ''} • Min. leads: {rec.min_qualified_leads}
                        </div>
                      </div>
                      <span style={{
                        padding: '4px 12px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 700,
                        background: rec.status === 'pending' ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)',
                        color: rec.status === 'pending' ? '#F59E0B' : '#10B981',
                      }}>{rec.status}</span>
                    </div>
                    <p style={{ fontSize: '0.9rem', marginBottom: '12px', lineHeight: 1.5 }}>{rec.rationale}</p>
                    
                    {rec.changes && rec.changes.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                        {rec.changes.map((ch, i) => (
                          <div key={i} style={{
                            padding: '8px 14px', borderRadius: '8px',
                            background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', gap: '8px'
                          }}>
                            <span style={{ fontWeight: 600 }}>{ch.pillar_slug}</span>
                            <span style={{ color: 'var(--text-secondary)' }}>{ch.from_pct}%</span>
                            <span>→</span>
                            <span style={{ fontWeight: 700, color: ch.delta > 0 ? '#10B981' : '#EF4444' }}>{ch.to_pct}%</span>
                            <span style={{ fontSize: '0.75rem', color: ch.delta > 0 ? '#10B981' : '#EF4444' }}>
                              {ch.delta > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                              {Math.abs(ch.delta)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {rec.status === 'pending' && (
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button className="btn btn-primary" onClick={() => decideRecommendation(rec.id, true)}
                          style={{ background: '#10B981' }}>
                          <CheckCircle2 size={16} /> Aceptar y Aplicar
                        </button>
                        <button className="btn btn-secondary" onClick={() => decideRecommendation(rec.id, false)}
                          style={{ color: '#EF4444' }}>
                          <XCircle size={16} /> Rechazar
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <Sparkles size={32} style={{ opacity: 0.4, marginBottom: '8px' }} />
                <p>No hay recomendaciones pendientes. Registra leads cualificados y genera una nueva recomendación.</p>
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
}
