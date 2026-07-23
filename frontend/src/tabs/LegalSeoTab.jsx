import React, { useCallback, useEffect, useState } from 'react';
import { Scale } from 'lucide-react';
import { api, getStoredUser } from '../api';

export default function LegalSeoTab({ notify }) {
  const [clusters, setClusters] = useState([]);
  const [briefs, setBriefs] = useState([]);
  const [claims, setClaims] = useState([]);
  const [busy, setBusy] = useState(false);
  const [clusterName, setClusterName] = useState('');
  const [primaryKw, setPrimaryKw] = useState('');
  const [briefTitle, setBriefTitle] = useState('');
  const [briefClusterId, setBriefClusterId] = useState('');
  const [pieceId, setPieceId] = useState('');
  const [evidenceClaimId, setEvidenceClaimId] = useState('');
  const [evidenceUrl, setEvidenceUrl] = useState('');

  const load = useCallback(async () => {
    try {
      const [c, b, cl] = await Promise.all([
        api('/seo-legal/clusters'),
        api('/seo-legal/briefs'),
        api('/seo-legal/claims'),
      ]);
      setClusters(c || []);
      setBriefs(b || []);
      setClaims(cl || []);
    } catch (e) {
      notify?.(e.message || 'No se pudo cargar SEO/Legal');
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  const createCluster = async () => {
    if (!clusterName.trim() || !primaryKw.trim()) {
      notify?.('Nombre y keyword primaria requeridos');
      return;
    }
    setBusy(true);
    try {
      await api('/seo-legal/clusters', {
        method: 'POST',
        body: JSON.stringify({
          name: clusterName.trim(),
          primary_keyword: primaryKw.trim(),
          keywords: [],
          jurisdiction: 'MX',
          search_intent: 'informational',
        }),
      });
      setClusterName('');
      setPrimaryKw('');
      await load();
      notify?.('Cluster SEO creado');
    } catch (e) {
      notify?.(e.message || 'Error cluster', 'error');
    } finally {
      setBusy(false);
    }
  };

  const createBrief = async () => {
    if (!briefTitle.trim()) {
      notify?.('Título del brief requerido');
      return;
    }
    setBusy(true);
    try {
      await api('/seo-legal/briefs', {
        method: 'POST',
        body: JSON.stringify({
          title: briefTitle.trim(),
          cluster_id: briefClusterId ? Number(briefClusterId) : null,
          jurisdiction: 'MX',
          created_by: getStoredUser()?.email || 'editor',
          angle: 'Qué debe revisar el consejo / GC',
        }),
      });
      setBriefTitle('');
      await load();
      notify?.('Brief creado');
    } catch (e) {
      notify?.(e.message || 'Error brief', 'error');
    } finally {
      setBusy(false);
    }
  };

  const extractClaims = async () => {
    const id = Number(pieceId);
    if (!id) {
      notify?.('Indica ID de content_piece');
      return;
    }
    setBusy(true);
    try {
      const res = await api(`/seo-legal/claims/from-piece/${id}`, {
        method: 'POST',
        body: JSON.stringify({ jurisdiction: 'MX' }),
      });
      await load();
      notify?.(`${res.created || 0} claims extraídos de pieza #${id}`);
    } catch (e) {
      notify?.(e.message || 'Extracción falló', 'error');
    } finally {
      setBusy(false);
    }
  };

  const addEvidence = async () => {
    const id = Number(evidenceClaimId);
    if (!id || !evidenceUrl.trim()) {
      notify?.('Claim ID y URL de evidencia requeridos');
      return;
    }
    setBusy(true);
    try {
      await api('/seo-legal/evidences', {
        method: 'POST',
        body: JSON.stringify({
          claim_id: id,
          source_url: evidenceUrl.trim(),
          verified_by: getStoredUser()?.email || 'legal',
          jurisdiction: 'MX',
        }),
      });
      setEvidenceUrl('');
      await load();
      notify?.('Evidencia registrada');
    } catch (e) {
      notify?.(e.message || 'Error evidencia', 'error');
    } finally {
      setBusy(false);
    }
  };

  const markSupported = async (claimId) => {
    setBusy(true);
    try {
      await api(`/seo-legal/claims/${claimId}/status`, {
        method: 'POST',
        body: JSON.stringify({
          status: 'supported',
          actor: getStoredUser()?.email || 'legal',
        }),
      });
      await load();
      notify?.(`Claim #${claimId} → supported`);
    } catch (e) {
      notify?.(e.message || 'Requiere evidencia primero', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass-panel" style={{ padding: 24 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
          <Scale size={22} /> SEO + Legal Authority
        </h2>
        <p style={{ color: 'var(--text-secondary)', margin: 0, maxWidth: 640 }}>
          Clusters, briefs y claims con evidencia. Un claim solo es &quot;supported&quot; con fuente;
          no basta el overlap léxico.
        </p>
      </div>

      <div className="grid-cards" style={{ marginBottom: 24 }}>
        <article className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 12 }}>Cluster SEO</h3>
          <input
            placeholder="Nombre del cluster"
            value={clusterName}
            onChange={(e) => setClusterName(e.target.value)}
            style={{ width: '100%', marginBottom: 8 }}
          />
          <input
            placeholder="Keyword primaria"
            value={primaryKw}
            onChange={(e) => setPrimaryKw(e.target.value)}
            style={{ width: '100%', marginBottom: 12 }}
          />
          <button type="button" className="btn btn-primary" disabled={busy} onClick={createCluster}>
            Crear cluster
          </button>
          <ul style={{ fontSize: '0.8rem', marginTop: 12, paddingLeft: 18 }}>
            {clusters.slice(0, 6).map((c) => (
              <li key={c.id}>
                #{c.id} {c.name} · {c.primary_keyword} · {c.jurisdiction}
              </li>
            ))}
            {clusters.length === 0 && <li>Sin clusters</li>}
          </ul>
        </article>

        <article className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 12 }}>Brief editorial</h3>
          <input
            placeholder="Título del brief"
            value={briefTitle}
            onChange={(e) => setBriefTitle(e.target.value)}
            style={{ width: '100%', marginBottom: 8 }}
          />
          <select
            value={briefClusterId}
            onChange={(e) => setBriefClusterId(e.target.value)}
            style={{ width: '100%', marginBottom: 12 }}
          >
            <option value="">Sin cluster</option>
            {clusters.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} {c.name}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={createBrief}>
            Crear brief
          </button>
          <ul style={{ fontSize: '0.8rem', marginTop: 12, paddingLeft: 18 }}>
            {briefs.slice(0, 6).map((b) => (
              <li key={b.id}>
                #{b.id} {b.title} · {b.status} · {b.jurisdiction}
              </li>
            ))}
            {briefs.length === 0 && <li>Sin briefs</li>}
          </ul>
        </article>

        <article className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 12 }}>Claims desde pieza</h3>
          <input
            type="number"
            placeholder="ID content_piece"
            value={pieceId}
            onChange={(e) => setPieceId(e.target.value)}
            style={{ width: '100%', marginBottom: 12 }}
          />
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={extractClaims}>
            Extraer claims
          </button>
          <h4 style={{ fontSize: '0.9rem', margin: '16px 0 8px' }}>Añadir evidencia</h4>
          <input
            type="number"
            placeholder="Claim ID"
            value={evidenceClaimId}
            onChange={(e) => setEvidenceClaimId(e.target.value)}
            style={{ width: '100%', marginBottom: 8 }}
          />
          <input
            placeholder="https://fuente…"
            value={evidenceUrl}
            onChange={(e) => setEvidenceUrl(e.target.value)}
            style={{ width: '100%', marginBottom: 12 }}
          />
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={addEvidence}>
            Registrar evidencia
          </button>
        </article>
      </div>

      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 12 }}>Claims recientes</h3>
      <div className="grid-cards">
        {claims.length === 0 && (
          <div className="glass-card" style={{ padding: 20, color: 'var(--text-secondary)' }}>
            Sin claims. Extrae desde una pieza o créalos vía API.
          </div>
        )}
        {claims.slice(0, 12).map((c) => (
          <article key={c.id} className="glass-card" style={{ padding: 16 }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
              #{c.id} · {c.status} · {c.jurisdiction} · {c.claim_type}
              {c.content_piece_id ? ` · pieza ${c.content_piece_id}` : ''}
            </div>
            <p style={{ margin: '0 0 10px', fontSize: '0.9rem', lineHeight: 1.45 }}>{c.claim_text}</p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 10px' }}>
              Evidencias: {(c.evidences || []).length}
            </p>
            {c.status !== 'supported' && (
              <button
                type="button"
                className="btn btn-primary"
                style={{ fontSize: '0.8rem', padding: '6px 10px' }}
                disabled={busy}
                onClick={() => markSupported(c.id)}
              >
                Marcar supported
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
