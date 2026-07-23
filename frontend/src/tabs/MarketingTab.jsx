import React, { useCallback, useEffect, useState } from 'react';
import { Link2, Mail, Megaphone, Package } from 'lucide-react';
import { api } from '../api';

const inputStyle = {
  padding: '10px 14px',
  borderRadius: '8px',
  background: 'rgba(0,0,0,0.3)',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.1)',
  minWidth: '140px',
  flex: 1,
};

export default function MarketingTab({ notify }) {
  const [offers, setOffers] = useState([]);
  const [links, setLinks] = useState([]);
  const [subs, setSubs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [offerName, setOfferName] = useState('');
  const [linkForm, setLinkForm] = useState({
    label: '',
    base_url: 'http://127.0.0.1:3002/',
    utm_source: 'linkedin',
    utm_medium: 'social',
    utm_campaign: '',
    service_offer_id: '',
  });
  const [previewUrl, setPreviewUrl] = useState('');
  const [subEmail, setSubEmail] = useState('');

  const load = useCallback(async () => {
    try {
      const [o, l, s] = await Promise.all([
        api('/marketing/offers?status=all'),
        api('/marketing/campaign-links'),
        api('/marketing/newsletter/subscribers'),
      ]);
      setOffers(o || []);
      setLinks(l || []);
      setSubs(s || []);
    } catch (e) {
      notify?.(e.message || 'No se pudo cargar Marketing');
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  const seedOffers = async () => {
    setBusy(true);
    try {
      const res = await api('/marketing/offers/seed-from-profile', { method: 'POST' });
      notify?.(`Ofertas creadas: ${res.count ?? 0}`);
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al sembrar ofertas', 'error');
    } finally {
      setBusy(false);
    }
  };

  const createOffer = async () => {
    if (!offerName.trim()) {
      notify?.('Nombre de servicio requerido');
      return;
    }
    setBusy(true);
    try {
      await api('/marketing/offers', {
        method: 'POST',
        body: JSON.stringify({ name: offerName.trim() }),
      });
      setOfferName('');
      notify?.('Servicio creado');
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al crear oferta', 'error');
    } finally {
      setBusy(false);
    }
  };

  const previewUtm = async () => {
    try {
      const body = {
        base_url: linkForm.base_url,
        utm_source: linkForm.utm_source || null,
        utm_medium: linkForm.utm_medium || null,
        utm_campaign: linkForm.utm_campaign || null,
      };
      const res = await api('/marketing/utm/preview', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      setPreviewUrl(res.tracked_url || '');
    } catch (e) {
      notify?.(e.message || 'Error en preview UTM', 'error');
    }
  };

  const saveLink = async () => {
    if (!linkForm.label.trim() || !linkForm.base_url.trim()) {
      notify?.('Etiqueta y URL base requeridas');
      return;
    }
    setBusy(true);
    try {
      await api('/marketing/campaign-links', {
        method: 'POST',
        body: JSON.stringify({
          label: linkForm.label.trim(),
          base_url: linkForm.base_url.trim(),
          utm_source: linkForm.utm_source || null,
          utm_medium: linkForm.utm_medium || null,
          utm_campaign: linkForm.utm_campaign || null,
          service_offer_id: linkForm.service_offer_id
            ? Number(linkForm.service_offer_id)
            : null,
        }),
      });
      notify?.('Enlace de campaña guardado');
      setLinkForm({ ...linkForm, label: '', utm_campaign: '' });
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al guardar enlace', 'error');
    } finally {
      setBusy(false);
    }
  };

  const addSubscriber = async () => {
    if (!subEmail.trim()) {
      notify?.('Email requerido');
      return;
    }
    setBusy(true);
    try {
      await api('/marketing/newsletter/subscribers', {
        method: 'POST',
        body: JSON.stringify({
          email: subEmail.trim(),
          status: 'pending',
          source_channel: 'admin',
        }),
      });
      setSubEmail('');
      notify?.('Suscriptor registrado');
      await load();
    } catch (e) {
      notify?.(e.message || 'Error al registrar suscriptor', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Megaphone size={24} style={{ color: '#F59E0B' }} /> Marketing & Atribución
      </h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
        Ofertas, enlaces UTM y lista newsletter. Los leads siguen en Resultados; aquí se arma la atribución.
      </p>

      <div style={{ marginBottom: '28px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Package size={18} style={{ color: '#06B6D4' }} /> Servicios / ofertas
        </h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <input
            style={inputStyle}
            placeholder="Nombre del servicio"
            value={offerName}
            onChange={(e) => setOfferName(e.target.value)}
          />
          <button className="btn btn-primary" disabled={busy} onClick={createOffer}>Crear</button>
          <button className="btn btn-secondary" disabled={busy} onClick={seedOffers}>
            Sembrar desde perfil
          </button>
        </div>
        <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-secondary)' }}>
          {offers.map((o) => (
            <li key={o.id}>
              <strong style={{ color: '#fff' }}>{o.name}</strong> · {o.slug} · {o.status}
            </li>
          ))}
          {offers.length === 0 && <li>Sin ofertas aún</li>}
        </ul>
      </div>

      <div style={{ marginBottom: '28px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Link2 size={18} style={{ color: '#10B981' }} /> Enlaces UTM
        </h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' }}>
          <input style={inputStyle} placeholder="Etiqueta" value={linkForm.label}
            onChange={(e) => setLinkForm({ ...linkForm, label: e.target.value })} />
          <input style={inputStyle} placeholder="URL base" value={linkForm.base_url}
            onChange={(e) => setLinkForm({ ...linkForm, base_url: e.target.value })} />
          <input style={inputStyle} placeholder="utm_source" value={linkForm.utm_source}
            onChange={(e) => setLinkForm({ ...linkForm, utm_source: e.target.value })} />
          <input style={inputStyle} placeholder="utm_medium" value={linkForm.utm_medium}
            onChange={(e) => setLinkForm({ ...linkForm, utm_medium: e.target.value })} />
          <input style={inputStyle} placeholder="utm_campaign" value={linkForm.utm_campaign}
            onChange={(e) => setLinkForm({ ...linkForm, utm_campaign: e.target.value })} />
          <select
            style={inputStyle}
            value={linkForm.service_offer_id}
            onChange={(e) => setLinkForm({ ...linkForm, service_offer_id: e.target.value })}
          >
            <option value="">Servicio (opc.)</option>
            {offers.filter((o) => o.status === 'active').map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <button className="btn btn-secondary" onClick={previewUtm}>Preview</button>
          <button className="btn btn-primary" disabled={busy} onClick={saveLink}>Guardar enlace</button>
        </div>
        {previewUrl && (
          <p style={{ fontSize: '0.85rem', wordBreak: 'break-all', color: '#10B981' }}>{previewUrl}</p>
        )}
        <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-secondary)' }}>
          {links.map((l) => (
            <li key={l.id} style={{ marginBottom: '6px' }}>
              <strong style={{ color: '#fff' }}>{l.label}</strong>
              <div style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>{l.tracked_url}</div>
            </li>
          ))}
          {links.length === 0 && <li>Sin enlaces guardados</li>}
        </ul>
      </div>

      <div>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Mail size={18} style={{ color: '#A78BFA' }} /> Newsletter (lista)
        </h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <input style={inputStyle} type="email" placeholder="email@ejemplo.com" value={subEmail}
            onChange={(e) => setSubEmail(e.target.value)} />
          <button className="btn btn-primary" disabled={busy} onClick={addSubscriber}>Registrar</button>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
          Solo captura de suscriptores — el envío ESP queda fuera del MVP.
        </p>
        <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-secondary)' }}>
          {subs.map((s) => (
            <li key={s.id}>{s.email} · {s.status}</li>
          ))}
          {subs.length === 0 && <li>Sin suscriptores</li>}
        </ul>
      </div>
    </section>
  );
}
