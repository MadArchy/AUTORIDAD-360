import React from 'react';
import { Bot, RefreshCw, Sparkles } from 'lucide-react';

export default function AgentsTab({
  isBusy,
  agentsCatalog,
  agentArticleId,
  setAgentArticleId,
  agentLimit,
  setAgentLimit,
  agentPipelineMode,
  setAgentPipelineMode,
  agentReason,
  setAgentReason,
  agentRunResult,
  onRefresh,
  onRunPipeline,
  onRunNamed,
  embedded = false,
}) {
  const body = (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          {!embedded && (
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Bot size={24} style={{ color: '#06B6D4' }} /> Agentes editoriales
            </h2>
          )}
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Pipelines editoriales (clasificar, descubrir, escribir). Usan los modelos configurados arriba.
            {agentsCatalog?.pipelines?.engine ? ` Motor: ${agentsCatalog.pipelines.engine}.` : ''}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh} disabled={isBusy('agents-run') || isBusy('agents-pipeline')}>
          <RefreshCw size={16} /> Actualizar
        </button>
      </div>

      <div className="glass-card" style={{ padding: '16px', marginBottom: '20px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'end' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          article_id (writer / article)
          <input
            value={agentArticleId}
            onChange={(e) => setAgentArticleId(e.target.value)}
            placeholder="ej. 42"
            style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)', minWidth: 120 }}
          />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Límite lote
          <input
            type="number"
            min={1}
            max={30}
            value={agentLimit}
            onChange={(e) => setAgentLimit(Number(e.target.value) || 3)}
            style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)', width: 80 }}
          />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Pipeline
          <select
            value={agentPipelineMode}
            onChange={(e) => setAgentPipelineMode(e.target.value)}
            style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}
          >
            <option value="ingest">ingest (clasificar lote)</option>
            <option value="discover">discover (scout web)</option>
            <option value="full">full (scout + clasificar)</option>
            <option value="article">article (completo por id)</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', paddingBottom: 8 }}>
          <input type="checkbox" checked={agentReason} onChange={(e) => setAgentReason(e.target.checked)} />
          Razonar antes (más lento)
        </label>
        <button
          className="btn btn-primary"
          onClick={onRunPipeline}
          disabled={isBusy('agents-pipeline') || isBusy('agents-run')}
        >
          <Sparkles size={16} /> {isBusy('agents-pipeline') ? 'Pipeline en curso… mira el robot' : 'Correr pipeline'}
        </button>
      </div>

      <div className="grid-cards" style={{ marginBottom: '24px' }}>
        {(agentsCatalog?.agents || []).map((ag) => (
          <div key={ag.name} className="glass-card" style={{ padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span className="score-tag">{ag.name}</span>
              <span className="status-badge status-verified">{ag.task_type}</span>
            </div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.45 }}>{ag.role}</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 12 }}>
              Tools: {(ag.tools || []).map((t) => t.name).join(', ')}
            </p>
            <button
              className="btn btn-secondary"
              style={{ width: '100%' }}
              onClick={() => onRunNamed(ag.name)}
              disabled={isBusy('agents-run') || isBusy('agents-pipeline')}
            >
              {isBusy('agents-run') ? 'Ejecutando…' : `Ejecutar ${ag.name}`}
            </button>
          </div>
        ))}
        {!agentsCatalog?.agents?.length && (
          <p style={{ color: 'var(--text-secondary)' }}>
            {agentsCatalog?.error
              ? `No se pudo cargar: ${agentsCatalog.error}`
              : 'Cargando catálogo de agentes…'}
          </p>
        )}
      </div>

      {agentRunResult && (
        <div className="glass-card" style={{ padding: '18px' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: 10 }}>
            Última corrida {agentRunResult.ok ? 'OK' : 'con errores'} · {agentRunResult.duration_ms ?? '—'} ms
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
            {agentRunResult.summary || `mode=${agentRunResult.mode || '—'}`}
          </p>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.78rem', maxHeight: 360, overflow: 'auto', background: 'rgba(0,0,0,0.35)', padding: 12, borderRadius: 8 }}>
            {JSON.stringify(agentRunResult, null, 2)}
          </pre>
        </div>
      )}
    </>
  );

  if (embedded) return body;
  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      {body}
    </section>
  );
}
