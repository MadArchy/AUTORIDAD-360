import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { api, getStoredUser } from '../api';

export default function RefreshTab({ notify }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [staleDays, setStaleDays] = useState(30);

  const load = useCallback(async () => {
    try {
      const rows = await api('/saas/refresh');
      setItems(rows || []);
    } catch (e) {
      notify?.(e.message || 'No se pudo cargar refresh');
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  const suggest = async () => {
    setBusy(true);
    try {
      const res = await api(`/saas/refresh/suggest?stale_days=${staleDays}&limit=20`, {
        method: 'POST',
      });
      notify?.(`Sugerencias nuevas: ${res.count ?? 0}`);
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al sugerir', 'error');
    } finally {
      setBusy(false);
    }
  };

  const decide = async (id, accept) => {
    setBusy(true);
    try {
      const actor = getStoredUser()?.email || getStoredUser()?.full_name || 'admin';
      await api(`/saas/refresh/${id}/decide`, {
        method: 'POST',
        body: JSON.stringify({ actor, accept }),
      });
      notify?.(accept ? 'Refresh aprobado' : 'Refresh descartado');
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al decidir', 'error');
    } finally {
      setBusy(false);
    }
  };

  const complete = async (id) => {
    setBusy(true);
    try {
      const actor = getStoredUser()?.email || 'admin';
      await api(`/saas/refresh/${id}/complete`, {
        method: 'POST',
        body: JSON.stringify({ actor }),
      });
      notify?.('Refresh marcado como hecho');
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al completar', 'error');
    } finally {
      setBusy(false);
    }
  };

  const startRevision = async (id) => {
    setBusy(true);
    try {
      const actor = getStoredUser()?.email || getStoredUser()?.full_name || 'admin';
      const row = await api(`/saas/refresh/${id}/start`, {
        method: 'POST',
        body: JSON.stringify({ actor }),
      });
      notify?.(`Revisión iniciada · pieza draft #${row.new_piece_id}`);
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al iniciar revisión', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass-panel" style={{ padding: 24 }}>
      <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
        <RefreshCw size={24} style={{ color: '#06B6D4' }} /> Refresh editorial
      </h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
        Flujo: sugerir → aprobar → <strong>iniciar revisión</strong> (crea draft v+1) → editar/aprobar en Contenido → marcar hecho.
      </p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16, alignItems: 'center' }}>
        <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Días sin update
          <input
            type="number"
            min={1}
            value={staleDays}
            onChange={(e) => setStaleDays(Number(e.target.value) || 30)}
            style={{
              marginLeft: 8,
              width: 80,
              padding: '8px 10px',
              borderRadius: 8,
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          />
        </label>
        <button className="btn btn-primary" disabled={busy} onClick={suggest}>
          Sugerir candidatos
        </button>
        <button className="btn btn-secondary" disabled={busy} onClick={load}>
          Recargar
        </button>
      </div>
      <div style={{ overflowX: 'auto', borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
          <thead>
            <tr style={{ background: 'rgba(6,182,212,0.12)' }}>
              <th style={{ padding: '10px 14px', textAlign: 'left' }}>ID</th>
              <th style={{ padding: '10px 14px', textAlign: 'left' }}>Pieza</th>
              <th style={{ padding: '10px 14px', textAlign: 'left' }}>Motivo</th>
              <th style={{ padding: '10px 14px', textAlign: 'left' }}>Estado</th>
              <th style={{ padding: '10px 14px', textAlign: 'left' }}>Notas</th>
              <th style={{ padding: '10px 14px', textAlign: 'left' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '10px 14px' }}>#{it.id}</td>
                <td style={{ padding: '10px 14px' }}>
                  piece #{it.piece_id}
                  {it.source_piece_version != null ? ` v${it.source_piece_version}` : ''}
                  {it.new_piece_id ? ` → new #${it.new_piece_id}` : ''}
                </td>
                <td style={{ padding: '10px 14px' }}>{it.reason}</td>
                <td style={{ padding: '10px 14px' }}>{it.status}</td>
                <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', maxWidth: 240 }}>
                  {it.notes || '—'}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {it.status === 'suggested' && (
                      <>
                        <button className="btn btn-primary" style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                          disabled={busy} onClick={() => decide(it.id, true)}>Aprobar</button>
                        <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                          disabled={busy} onClick={() => decide(it.id, false)}>Descartar</button>
                      </>
                    )}
                    {it.status === 'approved' && (
                      <button className="btn btn-primary" style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                        disabled={busy} onClick={() => startRevision(it.id)}>Iniciar revisión</button>
                    )}
                    {(it.status === 'approved' || it.status === 'in_progress') && (
                      <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                        disabled={busy} onClick={() => complete(it.id)}>Marcar hecho</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 20, textAlign: 'center', color: 'var(--text-secondary)' }}>
                  Sin ítems. Genera sugerencias o espera piezas antiguas.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
