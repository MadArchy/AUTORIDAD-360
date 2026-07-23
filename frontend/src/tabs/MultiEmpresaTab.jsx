import React, { useCallback, useEffect, useState } from 'react';
import { Building2, Globe, Users, UserPlus, Award, Send, Palette, CreditCard } from 'lucide-react';
import { api } from '../api';

const fieldStyle = {
  padding: '10px 14px',
  borderRadius: '8px',
  background: 'rgba(0,0,0,0.3)',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.1)',
};

export default function MultiEmpresaTab({
  orgContext,
  orgs,
  orgMembers,
  orgClients,
  orgRoles,
  newMember,
  setNewMember,
  addMember,
  newClient,
  setNewClient,
  onboardClient,
  notify,
  onOrgRefresh,
}) {
  const [plans, setPlans] = useState([]);
  const [saas, setSaas] = useState(null);
  const [planCode, setPlanCode] = useState('pilot');
  const [branding, setBranding] = useState({
    display_name: '',
    logo_url: '',
    primary_color: '',
    public_tagline: '',
  });
  const [hostname, setHostname] = useState('');
  const [busy, setBusy] = useState(false);

  const loadSaas = useCallback(async () => {
    try {
      const [p, me] = await Promise.all([
        api('/saas/plans'),
        api('/saas/me'),
      ]);
      setPlans(p || []);
      setSaas(me);
      setPlanCode(me?.plan_code || 'pilot');
      const b = me?.branding || {};
      setBranding({
        display_name: b.display_name || '',
        logo_url: b.logo_url || '',
        primary_color: b.primary_color || '',
        public_tagline: b.public_tagline || '',
      });
    } catch (e) {
      notify?.(e.message || 'No se pudo cargar SaaS');
    }
  }, [notify]);

  useEffect(() => {
    loadSaas();
  }, [loadSaas]);

  const savePlan = async () => {
    setBusy(true);
    try {
      await api('/saas/plan', {
        method: 'PUT',
        body: JSON.stringify({ plan_code: planCode }),
      });
      notify?.('Plan actualizado');
      await loadSaas();
      onOrgRefresh?.();
    } catch (e) {
      notify?.(e.message || 'Error al guardar plan', 'error');
    } finally {
      setBusy(false);
    }
  };

  const saveBranding = async () => {
    setBusy(true);
    try {
      await api('/saas/branding', {
        method: 'PATCH',
        body: JSON.stringify(branding),
      });
      notify?.('Branding guardado');
      await loadSaas();
      onOrgRefresh?.();
    } catch (e) {
      notify?.(e.message || 'Error branding', 'error');
    } finally {
      setBusy(false);
    }
  };

  const addDomain = async () => {
    if (!hostname.trim()) return notify?.('Hostname requerido');
    setBusy(true);
    try {
      await api('/saas/domains', {
        method: 'POST',
        body: JSON.stringify({ hostname: hostname.trim(), is_primary: true }),
      });
      setHostname('');
      notify?.('Dominio registrado (pending)');
      await loadSaas();
    } catch (e) {
      notify?.(e.message || 'Error dominio', 'error');
    } finally {
      setBusy(false);
    }
  };

  const verifyDomain = async (id) => {
    setBusy(true);
    try {
      await api(`/saas/domains/${id}/verify`, { method: 'POST' });
      notify?.('Dominio verificado (manual)');
      await loadSaas();
    } catch (e) {
      notify?.(e.message || 'Error verify', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
{true && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Building2 size={24} style={{ color: '#8B5CF6' }} /> Multiempresa / Multicliente
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            Gestión de organizaciones, miembros y clientes. Cada agencia ve solo sus datos; cada cliente ve solo su información.
          </p>

          {/* Context Info */}
          {orgContext && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #8B5CF6' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Usuario Activo</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{orgContext.user?.full_name}</div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{orgContext.user?.email}</div>
              </div>
              <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #06B6D4' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Organización</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{orgContext.organization?.name}</div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {orgContext.organization?.org_type} • {orgContext.organization?.plan_label || orgContext.organization?.plan_code || saas?.plan_label || '—'}
                </div>
              </div>
              <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #10B981' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Rol</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{orgContext.role}</div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {orgContext.user?.is_superadmin ? 'Superadmin' : 'Miembro'}
                </div>
              </div>
            </div>
          )}

          <div style={{ marginBottom: 28 }} className="glass-card">
            <div style={{ padding: 20 }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <CreditCard size={18} style={{ color: '#F59E0B' }} /> Plan SaaS
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                Entitlements (sin cobro). BYOK y white-label según plan.
              </p>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
                <select style={fieldStyle} value={planCode} onChange={(e) => setPlanCode(e.target.value)}>
                  {(plans.length ? plans : [{ code: 'pilot', label: 'Piloto' }]).map((p) => (
                    <option key={p.code} value={p.code}>{p.label || p.code} ({p.code})</option>
                  ))}
                </select>
                <button className="btn btn-primary" disabled={busy} onClick={savePlan}>Guardar plan</button>
              </div>
              {saas?.limits && (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Seats {saas.limits.max_seats} · AI/día {saas.limits.max_ai_daily_requests} · BYOK {saas.limits.byok_allowed ? 'sí' : 'no'} · WL {saas.limits.white_label ? 'sí' : 'no'}
                </div>
              )}
            </div>
          </div>

          <div style={{ marginBottom: 28 }} className="glass-card">
            <div style={{ padding: 20 }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Palette size={18} style={{ color: '#EC4899' }} /> White-label
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginBottom: 12 }}>
                <input style={fieldStyle} placeholder="display_name" value={branding.display_name}
                  onChange={(e) => setBranding({ ...branding, display_name: e.target.value })} />
                <input style={fieldStyle} placeholder="logo_url" value={branding.logo_url}
                  onChange={(e) => setBranding({ ...branding, logo_url: e.target.value })} />
                <input style={fieldStyle} placeholder="primary_color (#0A7)" value={branding.primary_color}
                  onChange={(e) => setBranding({ ...branding, primary_color: e.target.value })} />
                <input style={fieldStyle} placeholder="public_tagline" value={branding.public_tagline}
                  onChange={(e) => setBranding({ ...branding, public_tagline: e.target.value })} />
              </div>
              <button className="btn btn-primary" disabled={busy} onClick={saveBranding}>Guardar branding</button>
              <div style={{ marginTop: 16 }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 8 }}>Dominios custom</h4>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
                  <input style={{ ...fieldStyle, flex: 1, minWidth: 180 }} placeholder="blog.cliente.com"
                    value={hostname} onChange={(e) => setHostname(e.target.value)} />
                  <button className="btn btn-secondary" disabled={busy} onClick={addDomain}>Añadir</button>
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-secondary)' }}>
                  {(saas?.domains || []).map((d) => (
                    <li key={d.id} style={{ marginBottom: 6 }}>
                      {d.hostname} · {d.status}
                      {d.status !== 'verified' && (
                        <button className="btn btn-secondary" style={{ marginLeft: 8, fontSize: '0.7rem', padding: '2px 8px' }}
                          disabled={busy} onClick={() => verifyDomain(d.id)}>Verificar</button>
                      )}
                    </li>
                  ))}
                  {(saas?.domains || []).length === 0 && <li>Sin dominios</li>}
                </ul>
              </div>
            </div>
          </div>

          {/* Organizations List */}
          <div style={{ marginBottom: '28px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Globe size={18} style={{ color: '#06B6D4' }} /> Organizaciones ({orgs.length})
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '12px' }}>
              {orgs.map(o => (
                <div key={o.id} className="glass-card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #8B5CF6, #6366F1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1rem' }}>
                    {o.name?.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{o.name}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{o.slug} • {o.org_type}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Members Table */}
          <div style={{ marginBottom: '28px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Users size={18} style={{ color: '#F59E0B' }} /> Miembros del Equipo ({orgMembers.length})
            </h3>
            <div style={{ overflowX: 'auto', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: 'rgba(139,92,246,0.15)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600 }}>Nombre</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600 }}>Email</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600 }}>Rol</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600 }}>Perfil</th>
                  </tr>
                </thead>
                <tbody>
                  {orgMembers.map(m => (
                    <tr key={m.membership_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '10px 16px', fontWeight: 600 }}>{m.full_name}</td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>{m.email}</td>
                      <td style={{ padding: '10px 16px' }}>
                        <span style={{
                          padding: '3px 10px',
                          borderRadius: '6px',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          background: m.role === 'superadmin' ? 'rgba(239,68,68,0.2)' :
                                     m.role === 'agency_admin' ? 'rgba(139,92,246,0.2)' :
                                     m.role === 'professional' ? 'rgba(16,185,129,0.2)' :
                                     'rgba(99,102,241,0.15)',
                          color: m.role === 'superadmin' ? '#EF4444' :
                                 m.role === 'agency_admin' ? '#A78BFA' :
                                 m.role === 'professional' ? '#10B981' :
                                 '#818CF8',
                        }}>{m.role}</span>
                      </td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>{m.profile_id || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Add Member Form */}
            <div className="glass-card" style={{ padding: '20px', marginTop: '16px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <UserPlus size={16} style={{ color: '#10B981' }} /> Agregar Miembro
              </h4>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <input
                  type="email" placeholder="Email"
                  value={newMember.email} onChange={e => setNewMember({...newMember, email: e.target.value})}
                  style={{ flex: 1, minWidth: '180px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input
                  type="text" placeholder="Nombre completo"
                  value={newMember.full_name} onChange={e => setNewMember({...newMember, full_name: e.target.value})}
                  style={{ flex: 1, minWidth: '180px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <select
                  value={newMember.role} onChange={e => setNewMember({...newMember, role: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                >
                  {orgRoles.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                <button className="btn btn-primary" onClick={addMember} style={{ whiteSpace: 'nowrap' }}>
                  <UserPlus size={16} /> Agregar
                </button>
              </div>
            </div>
          </div>

          {/* Clients / Profiles */}
          <div style={{ marginBottom: '28px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Award size={18} style={{ color: '#10B981' }} /> Clientes / Perfiles Profesionales ({orgClients.length})
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
              {orgClients.map(c => (
                <div key={c.id} className="glass-card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                    <div style={{ width: '44px', height: '44px', borderRadius: '50%', background: 'linear-gradient(135deg, #10B981, #059669)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1.1rem' }}>
                      {c.full_name?.charAt(0)}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '1rem' }}>{c.full_name}</div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{c.title || 'Sin título'}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    Slug: <code style={{ color: '#8B5CF6' }}>{c.slug}</code> • Org: {c.organization_id}
                  </div>
                </div>
              ))}
            </div>

            {/* Onboard Client Form */}
            <div className="glass-card" style={{ padding: '20px', marginTop: '16px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <UserPlus size={16} style={{ color: '#8B5CF6' }} /> Onboarding — Nuevo Cliente
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
                <input
                  type="text" placeholder="Slug (ej: ana-martinez)"
                  value={newClient.slug} onChange={e => setNewClient({...newClient, slug: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input
                  type="text" placeholder="Nombre completo"
                  value={newClient.full_name} onChange={e => setNewClient({...newClient, full_name: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input
                  type="text" placeholder="Título profesional"
                  value={newClient.title} onChange={e => setNewClient({...newClient, title: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input
                  type="email" placeholder="Email"
                  value={newClient.email} onChange={e => setNewClient({...newClient, email: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <input
                  type="text" placeholder="Bio / descripción"
                  value={newClient.bio} onChange={e => setNewClient({...newClient, bio: e.target.value})}
                  style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <button className="btn btn-primary" onClick={onboardClient}>
                  <Send size={16} /> Onboard
                </button>
              </div>
            </div>
          </div>

          {/* Roles Reference */}
          <div className="glass-card" style={{ padding: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginRight: '8px' }}>Roles del sistema:</span>
            {orgRoles.map(r => (
              <span key={r} style={{
                padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 600,
                background: 'rgba(99,102,241,0.12)', color: '#A78BFA', border: '1px solid rgba(139,92,246,0.2)'
              }}>{r}</span>
            ))}
          </div>
        </section>
      )}

    </>
  );
}
