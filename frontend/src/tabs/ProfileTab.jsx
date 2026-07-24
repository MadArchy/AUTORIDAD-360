import React from 'react';
import { Plus, RotateCcw, Search, Sliders, Trash2 } from 'lucide-react';

export default function ProfileTab({
  profile,
  pillarDrafts,
  setPillarDrafts,
  saveProfilePercentages,
  themeDrafts,
  setThemeDrafts,
  saveSearchThemes,
  resetSearchThemes,
  applyPdfPillarMix,
}) {
  const themes = themeDrafts || [];

  const updateTheme = (index, patch) => {
    setThemeDrafts(themes.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  };

  const removeTheme = (index) => {
    setThemeDrafts(themes.filter((_, i) => i !== index));
  };

  const addTheme = () => {
    const nextId = themes.length + 1;
    setThemeDrafts([
      ...themes,
      {
        id: nextId,
        slug: `tema-custom-${nextId}`,
        name: '',
        monitor: '',
        why: '',
        editorial_angle: '',
        queries: [],
        is_active: true,
      },
    ]);
  };

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

          {/* Temas de búsqueda = tipologías del PDF + custom */}
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Search size={20} style={{ color: 'var(--accent-cyan)' }} /> Temas de búsqueda (tipologías)
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '16px', maxWidth: '820px' }}>
            Estos temas alimentan la patrulla web y los motores de búsqueda. Incluyen las 11 tipologías del documento
            de Juan Vásquez; puedes editar queries, desactivar o agregar temas nuevos.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
            {themes.map((theme, index) => (
              <div key={`${theme.slug}-${index}`} className="glass-card" style={{ padding: '18px', opacity: theme.is_active === false ? 0.55 : 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '10px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '220px' }}>
                    <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Nombre del tema</label>
                    <input
                      value={theme.name || ''}
                      onChange={(e) => updateTheme(index, { name: e.target.value })}
                      placeholder="Ej. Política y regulación de IA"
                      style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)' }}
                    />
                  </div>
                  <div style={{ width: '180px' }}>
                    <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Slug</label>
                    <input
                      value={theme.slug || ''}
                      onChange={(e) => updateTheme(index, { slug: e.target.value })}
                      style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)' }}
                    />
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', marginTop: '18px' }}>
                    <input
                      type="checkbox"
                      checked={theme.is_active !== false}
                      onChange={(e) => updateTheme(index, { is_active: e.target.checked })}
                    />
                    Activo
                  </label>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => removeTheme(index)}
                    title="Eliminar tema"
                    style={{ marginTop: '14px', padding: '8px 10px' }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Qué monitorear</label>
                <textarea
                  value={theme.monitor || ''}
                  onChange={(e) => updateTheme(index, { monitor: e.target.value })}
                  rows={2}
                  style={{ width: '100%', marginTop: '4px', marginBottom: '10px', padding: '8px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)', resize: 'vertical' }}
                />

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '10px' }}>
                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Por qué sirve</label>
                    <textarea
                      value={theme.why || ''}
                      onChange={(e) => updateTheme(index, { why: e.target.value })}
                      rows={2}
                      style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)', resize: 'vertical' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Ángulo editorial</label>
                    <textarea
                      value={theme.editorial_angle || ''}
                      onChange={(e) => updateTheme(index, { editorial_angle: e.target.value })}
                      rows={2}
                      style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)', resize: 'vertical' }}
                    />
                  </div>
                </div>

                <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Queries de búsqueda (una por línea)
                </label>
                <textarea
                  value={(theme.queries || []).join('\n')}
                  onChange={(e) =>
                    updateTheme(index, {
                      queries: e.target.value
                        .split('\n')
                        .map((q) => q.trim())
                        .filter(Boolean),
                    })
                  }
                  rows={3}
                  placeholder={'regulación inteligencia artificial México 2026\nUS AI regulation executive order'}
                  style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', color: '#FFF', border: '1px solid rgba(255,255,255,0.2)', fontFamily: 'ui-monospace, monospace', fontSize: '0.82rem', resize: 'vertical' }}
                />
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '28px' }}>
            <button type="button" className="btn" onClick={addTheme}>
              <Plus size={16} style={{ marginRight: 6 }} /> Agregar tema
            </button>
            <button type="button" className="btn btn-primary" onClick={saveSearchThemes}>
              Guardar temas de búsqueda
            </button>
            <button type="button" className="btn" onClick={resetSearchThemes} title="Restaurar las 11 tipologías del PDF">
              <RotateCcw size={16} style={{ marginRight: 6 }} /> Restaurar tipologías PDF
            </button>
          </div>

          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={20} style={{ color: 'var(--accent-cyan)' }} /> Pilares Editoriales y Corrección Automática de Cuota
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '16px', maxWidth: '820px' }}>
            Mix alineado al PDF de Juan (IA, gobernanza, PI, MX–US). Si un pilar va bajo meta, Top 10 y Hoy lo priorizan.
          </p>

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
                  <span>Cobertura del Mes: <strong>{p.current_month_pct}%</strong> ({p.current_month_count} piezas)</span>
                  <span>Meta Configurada: <strong>{p.target_percentage}%</strong></span>
                </div>
              </div>
            ))}
          </div>

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
          <div style={{ marginTop: '24px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={saveProfilePercentages}>
              Guardar porcentajes editoriales
            </button>
            {applyPdfPillarMix && (
              <button
                type="button"
                className="btn"
                onClick={applyPdfPillarMix}
                title="Aplica 30/25/20/15/10 del documento de Juan"
              >
                <RotateCcw size={16} style={{ marginRight: 6 }} /> Aplicar mix PDF
              </button>
            )}
          </div>
        </section>
      )}
    </>
  );
}
