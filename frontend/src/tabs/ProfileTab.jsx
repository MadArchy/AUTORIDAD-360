import React from 'react';
import { Sliders } from 'lucide-react';

export default function ProfileTab({
  profile,
  pillarDrafts,
  setPillarDrafts,
  saveProfilePercentages
}) {
  return (
    <>
{!profile && (
        <section className="glass-panel" style={{ padding: '24px', color: 'var(--text-secondary)' }}>
          Cargando perfil estratégico…
        </section>
      )}
      {profile && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
            <div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>{profile.full_name}</h2>
              <p style={{ color: 'var(--accent-cyan)', fontWeight: 600, fontSize: '1rem' }}>{profile.title}</p>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '6px', maxWidth: '800px' }}>{profile.bio}</p>
            </div>
            <span className="brand-badge" style={{ fontSize: '0.85rem' }}>Perfil Piloto Activo</span>
          </div>

          {/* Target Audiences & Services */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '28px' }}>
            <div className="glass-card" style={{ padding: '18px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px', color: 'var(--accent-purple)' }}>Públicos Objetivo</h3>
              <ul style={{ paddingLeft: '18px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                {profile.target_audiences.map((aud, i) => <li key={i} style={{ marginBottom: '4px' }}>{aud}</li>)}
              </ul>
            </div>

            <div className="glass-card" style={{ padding: '18px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px', color: 'var(--accent-cyan)' }}>Servicios Estratégicos</h3>
              <ul style={{ paddingLeft: '18px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                {profile.services.map((srv, i) => <li key={i} style={{ marginBottom: '4px' }}>{srv}</li>)}
              </ul>
            </div>
          </div>

          {/* Pilares Editoriales y Corrección de Cuotas */}
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={20} style={{ color: 'var(--accent-cyan)' }} /> Pilares Editoriales y Corrección Automática de Cuota
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {profile.pillars.map((p) => (
              <div key={p.id} className="glass-card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div>
                    <strong style={{ fontSize: '1.05rem' }}>{p.name}</strong>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{p.description}</p>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>ESTADO DE CUOTA</span>
                      <span className={`status-badge ${p.quota_status === 'below_quota' ? 'status-pending' : 'status-verified'}`}>
                        {p.quota_status === 'below_quota' ? `Bajo Meta (Boost x${p.quota_boost})` : 'Balanceado'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Meta %:</span>
                      <input 
                        type="number" 
                        value={pillarDrafts[p.slug] ?? p.target_percentage}
                        onChange={(e) => setPillarDrafts({ ...pillarDrafts, [p.slug]: Number(e.target.value) })}
                        style={{ width: '65px', padding: '6px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)', textAlign: 'center', fontWeight: 700 }}
                      />
                    </div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div style={{ width: '100%', background: 'rgba(255,255,255,0.08)', height: '10px', borderRadius: '5px', overflow: 'hidden', marginTop: '10px' }}>
                  <div 
                    style={{ 
                      width: `${Math.min(p.current_month_pct, 100)}%`, 
                      background: p.quota_status === 'below_quota' ? 'linear-gradient(90deg, #F59E0B, #10B981)' : 'linear-gradient(90deg, #3B82F6, #8B5CF6)', 
                      height: '100%',
                      borderRadius: '5px',
                      transition: 'width 0.4s ease'
                    }} 
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
                  <span>Cobertura del Mes: <strong>{p.current_month_pct}%</strong> ({p.current_month_count} artículos)</span>
                  <span>Meta Configurada: <strong>{p.target_percentage}%</strong></span>
                </div>
              </div>
            ))}
          </div>

          {/* Mercados Objetivo */}
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '28px 0 16px 0' }}>Distribución por Mercado Objetivo (MX vs US)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {profile.markets.map((m) => (
              <div key={m.id} className="glass-card" style={{ padding: '18px', textAlign: 'center' }}>
                <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>{m.market_name} ({m.market_code})</span>
                <p style={{ fontSize: '1.4rem', fontWeight: 800, margin: '8px 0' }}>{m.target_percentage}%</p>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Meta de cobertura de contenido cross-border</p>
              </div>
            ))}
          </div>
          <div style={{ marginTop: '24px' }}>
            <button className="btn btn-primary" onClick={saveProfilePercentages}>
              Guardar porcentajes editoriales
            </button>
          </div>
        </section>
      )}

    </>
  );
}
