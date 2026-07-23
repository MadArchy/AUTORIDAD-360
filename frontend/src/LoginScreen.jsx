import React, { useState } from 'react';
import { ShieldCheck, LogIn, Loader2 } from 'lucide-react';
import { login } from './api';

export default function LoginScreen({ onSuccess }) {
  const showDevAccess = import.meta.env.DEV;
  const [email, setEmail] = useState(showDevAccess ? 'agencia@autoridad360.local' : '');
  const [password, setPassword] = useState(showDevAccess ? 'admin123' : '');
  const [orgSlug, setOrgSlug] = useState(showDevAccess ? 'agencia-piloto' : '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const data = await login(email.trim(), password, orgSlug.trim() || 'agencia-piloto');
      onSuccess?.(data);
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="login-card glass-panel" onSubmit={submit}>
        <div className="login-brand">
          <ShieldCheck size={32} style={{ color: 'var(--accent-blue)' }} />
          <h1>Autoridad 360</h1>
          <p>Inteligencia editorial para decisiones con autoridad</p>
        </div>

        <label>
          Email
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            required
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
            required
          />
        </label>
        <label>
          Organización (slug)
          <input
            value={orgSlug}
            onChange={(ev) => setOrgSlug(ev.target.value)}
            placeholder="agencia-piloto"
          />
        </label>

        {error && <div className="login-error">{error}</div>}

        <button type="submit" className="btn btn-primary" disabled={busy} style={{ width: '100%' }}>
          {busy ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
          {busy ? ' Entrando…' : ' Entrar'}
        </button>

        {showDevAccess && (
          <p className="login-hint">
            Acceso local: <code>agencia@autoridad360.local</code> / <code>admin123</code>
          </p>
        )}
      </form>
    </div>
  );
}
