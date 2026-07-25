import React, { useState } from 'react';
import { Bot, Check, RefreshCw, Send, Sparkles } from 'lucide-react';
import { api } from '../api';

const QUICK = [
  { label: 'Más profesional', prompt: 'Reescribe con tono más jurídico y profesional, sin hype.' },
  { label: 'Más corto', prompt: 'Hazlo más conciso conservando el mensaje clave.' },
  { label: 'Mejor gancho', prompt: 'Mejora el gancho inicial para redes profesionales.' },
  { label: 'CTA claro', prompt: 'Añade o mejora un CTA claro al final sin sonar comercial.' },
];

export default function PieceCopilotPanel({
  pieceId,
  draftText = '',
  providerMode = 'auto',
  onApply,
  notify,
  disabled = false,
}) {
  const [instruction, setInstruction] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!pieceId) {
    return (
      <div className="glass-card" style={{ padding: 16, color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
        Genera el formato para activar el chat de IA.
      </div>
    );
  }

  const run = async (prompt) => {
    const text = (prompt || instruction || '').trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api(`/content/pieces/${pieceId}/copilot`, {
        method: 'POST',
        body: JSON.stringify({
          instruction: text,
          draft_text: draftText,
          provider_mode: providerMode,
        }),
      });
      setResult(data);
      setInstruction('');
    } catch (e) {
      setError(e.message || 'Error del copiloto');
      notify?.(e.message || 'Error del copiloto', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="glass-card"
      style={{ padding: 16, borderLeft: '3px solid var(--accent-cyan)', display: 'flex', flexDirection: 'column', gap: 12 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Bot size={18} style={{ color: 'var(--accent-cyan)' }} />
        <strong style={{ fontSize: '0.95rem' }}>Chat IA · este formato</strong>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          {providerMode === 'local' ? 'Ollama' : providerMode === 'cloud' ? 'API key' : 'Auto'}
        </span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {QUICK.map((q) => (
          <button
            key={q.label}
            type="button"
            className="btn btn-secondary"
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
            disabled={loading || disabled}
            onClick={() => run(q.prompt)}
          >
            <Sparkles size={12} style={{ marginRight: 4 }} />
            {q.label}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              run();
            }
          }}
          placeholder="Pide una mejora o corrección…"
          disabled={loading || disabled}
          style={{
            flex: 1,
            padding: '10px 12px',
            borderRadius: 8,
            background: 'rgba(0,0,0,0.35)',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.15)',
          }}
        />
        <button type="button" className="btn btn-primary" disabled={loading || disabled || !instruction.trim()} onClick={() => run()}>
          {loading ? <RefreshCw size={16} className="spin" /> : <Send size={16} />}
        </button>
      </div>

      {error && <p style={{ color: '#EF4444', fontSize: '0.85rem', margin: 0 }}>{error}</p>}

      {result?.refined_content && (
        <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6 }}>
            Sugerencia {result.model_used ? `· ${result.model_used}` : ''}
          </div>
          <pre
            style={{
              margin: 0,
              whiteSpace: 'pre-wrap',
              fontFamily: 'inherit',
              fontSize: '0.85rem',
              maxHeight: 180,
              overflow: 'auto',
              color: 'var(--text-secondary)',
            }}
          >
            {result.refined_content}
          </pre>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 10, padding: '6px 12px', fontSize: '0.8rem' }}
            onClick={() => {
              onApply?.(result.refined_content);
              setResult(null);
              notify?.('Sugerencia aplicada al editor. Guarda para persistir.', 'success');
            }}
          >
            <Check size={14} style={{ marginRight: 6 }} /> Aplicar al editor
          </button>
        </div>
      )}
    </div>
  );
}
