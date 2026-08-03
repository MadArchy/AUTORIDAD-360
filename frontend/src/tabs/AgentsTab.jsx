import React, { useEffect, useMemo } from 'react';
import { Activity, Bot, Play, RefreshCw, Sparkles } from 'lucide-react';

function statusTone(status) {
  if (status === 'running' || status === 'queued') return { bg: 'rgba(6,182,212,0.2)', color: '#67e8f9', label: 'ACTIVO' };
  if (status === 'completed') return { bg: 'rgba(34,197,94,0.18)', color: '#86efac', label: 'OK' };
  if (status === 'failed') return { bg: 'rgba(239,68,68,0.18)', color: '#fca5a5', label: 'ERROR' };
  return { bg: 'rgba(148,163,184,0.15)', color: '#cbd5e1', label: 'IDLE' };
}

export default function AgentsTab({
  isBusy,
  agentsCatalog,
  agentBoard,
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
  onRunAutoCycle,
  embedded = false,
}) {
  const boardAgents = agentBoard?.agents || agentsCatalog?.board?.agents || [];
  const cycle = agentBoard?.cycle || agentsCatalog?.board?.cycle || null;
  const activeNames = agentBoard?.active || agentsCatalog?.board?.active || [];

  useEffect(() => {
    if (!onRefresh) return undefined;
    const busyCycle = cycle?.status === 'running' || activeNames.length > 0;
    if (!busyCycle) return undefined;
    const id = setInterval(() => onRefresh(), 4000);
    return () => clearInterval(id);
  }, [onRefresh, cycle?.status, activeNames.length]);

  const sortedBoard = useMemo(
    () => [...boardAgents].sort((a, b) => (a.priority || 99) - (b.priority || 99)),
    [boardAgents]
  );

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
            Trabajan en automático por prioridad (beat horario + ciclo manual). Tablero en vivo de función y estado.
            {agentsCatalog?.pipelines?.engine ? ` Motor: ${agentsCatalog.pipelines.engine}.` : ''}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary"
            onClick={onRunAutoCycle}
            disabled={isBusy('agents-auto') || isBusy('agents-run') || isBusy('agents-pipeline') || cycle?.status === 'running'}
          >
            <Play size={16} /> {isBusy('agents-auto') || cycle?.status === 'running' ? 'Ciclo en curso…' : 'Correr ciclo automático'}
          </button>
          <button className="btn btn-secondary" onClick={onRefresh} disabled={isBusy('agents-run') || isBusy('agents-pipeline')}>
            <RefreshCw size={16} /> Actualizar
          </button>
        </div>
      </div>

      <div className="glass-card" style={{ padding: '16px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
            <Activity size={18} style={{ color: '#06B6D4' }} /> Tablero de agentes
          </h3>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            {cycle?.status === 'running' ? (
              <>Ciclo <strong style={{ color: '#67e8f9' }}>activo</strong> · fase {cycle.phase || '—'} · agente {cycle.current_agent || '—'}</>
            ) : (
              <>Ciclo {cycle?.status || 'idle'}{cycle?.summary ? ` · ${cycle.summary}` : ''}</>
            )}
            {activeNames.length > 0 ? ` · activos: ${activeNames.join(', ')}` : ''}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
          {sortedBoard.map((ag) => {
            const tone = statusTone(ag.status);
            return (
              <div
                key={ag.name}
                style={{
                  padding: '14px',
                  borderRadius: 10,
                  background: 'rgba(0,0,0,0.28)',
                  border: ag.status === 'running' ? '1px solid rgba(6,182,212,0.55)' : '1px solid rgba(255,255,255,0.08)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
                  <span className="score-tag">P{ag.priority} · {ag.name}</span>
                  <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '2px 8px', borderRadius: 999, background: tone.bg, color: tone.color }}>
                    {tone.label}
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 8, lineHeight: 1.4 }}>
                  {ag.function || ag.role}
                </p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
                  Fase: {ag.phase || '—'}
                  {ag.current_tool || ag.current_step ? ` · Ahora: ${ag.current_tool || ag.current_step}` : ''}
                </p>
                {ag.summary && (
                  <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.35 }}>
                    {ag.summary}
                  </p>
                )}
                {ag.error && (
                  <p style={{ fontSize: '0.72rem', color: '#fca5a5', marginTop: 6 }}>{ag.error}</p>
                )}
              </div>
            );
          })}
          {!sortedBoard.length && (
            <p style={{ color: 'var(--text-secondary)' }}>Cargando tablero de prioridad…</p>
          )}
        </div>
      </div>

      <div className="glass-card" style={{ padding: '16px', marginBottom: '20px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'end' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          article_id (writer / Juan / article)
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
          Pipeline manual
          <select
            value={agentPipelineMode}
            onChange={(e) => setAgentPipelineMode(e.target.value)}
            style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}
          >
            <option value="ingest">ingest (clasificar lote)</option>
            <option value="discover">discover (scout web)</option>
            <option value="full">full (scout + clasificar)</option>
            <option value="article">article (completo por id)</option>
            <option value="trends">trends (notas redes)</option>
            <option value="juan_practice">juan_practice (editorial + AI gov + IP)</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', paddingBottom: 8 }}>
          <input type="checkbox" checked={agentReason} onChange={(e) => setAgentReason(e.target.checked)} />
          Razonar antes (más lento)
        </label>
        <button
          className="btn btn-primary"
          onClick={onRunPipeline}
          disabled={isBusy('agents-pipeline') || isBusy('agents-run') || isBusy('agents-auto')}
        >
          <Sparkles size={16} /> {isBusy('agents-pipeline') ? 'Pipeline en curso…' : 'Correr pipeline'}
        </button>
      </div>

      <div className="grid-cards" style={{ marginBottom: '24px' }}>
        {(agentsCatalog?.agents || [])
          .slice()
          .sort((a, b) => (a.priority || 99) - (b.priority || 99))
          .map((ag) => {
            const live = sortedBoard.find((b) => b.name === ag.name);
            const tone = statusTone(live?.status || 'idle');
            return (
              <div key={ag.name} className="glass-card" style={{ padding: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, gap: 8 }}>
                  <span className="score-tag">P{ag.priority ?? '—'} · {ag.name}</span>
                  <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '2px 8px', borderRadius: 999, background: tone.bg, color: tone.color }}>
                    {tone.label}
                  </span>
                </div>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.45 }}>
                  {ag.function || ag.role}
                </p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 12 }}>
                  Tools: {(ag.tools || []).map((t) => t.name).join(', ')}
                </p>
                <button
                  className="btn btn-secondary"
                  style={{ width: '100%' }}
                  onClick={() => onRunNamed(ag.name)}
                  disabled={isBusy('agents-run') || isBusy('agents-pipeline') || isBusy('agents-auto')}
                >
                  {isBusy('agents-run') ? 'Ejecutando…' : `Ejecutar ${ag.name}`}
                </button>
              </div>
            );
          })}
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
            {agentRunResult.summary || agentRunResult.message || `mode=${agentRunResult.mode || '—'}`}
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
