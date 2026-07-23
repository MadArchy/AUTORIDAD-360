import React, { useEffect, useMemo, useState } from 'react';
import { Cpu, Wifi, WifiOff, Clock, Bot } from 'lucide-react';

/**
 * Robot de estado: conexión Ollama + trabajo en curso + ETA.
 */
export default function OllamaRobot({ status, job, onRefresh }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!job?.startedAt) return undefined;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [job?.startedAt]);

  const connected = Boolean(status?.connected);
  const working = Boolean(job?.key);
  const mode = working ? 'working' : connected ? 'idle' : 'offline';

  const elapsedSec = job?.startedAt ? Math.max(0, Math.floor((now - job.startedAt) / 1000)) : 0;
  const etaSec = Number(job?.etaSec || 0);
  const remaining = etaSec > 0 ? Math.max(0, etaSec - elapsedSec) : null;
  const progress = etaSec > 0 ? Math.min(99, Math.round((elapsedSec / etaSec) * 100)) : null;

  const headline = useMemo(() => {
    if (working) return job.label || 'Trabajando…';
    if (connected) return 'Listo y conectado a Ollama';
    return 'Ollama no responde';
  }, [working, connected, job]);

  const detail = useMemo(() => {
    if (working && remaining != null) {
      return `Estimado restante: ~${formatDuration(remaining)} (transcurridos ${formatDuration(elapsedSec)})`;
    }
    if (working) return `En curso… ${formatDuration(elapsedSec)}`;
    if (connected) {
      const model = status?.model || 'modelo local';
      const lat = status?.latency_ms != null ? `${status.latency_ms} ms` : '—';
      return `${model} · latencia ${lat}`;
    }
    return status?.error || 'Arranca Ollama o revisa OLLAMA_BASE_URL';
  }, [working, remaining, elapsedSec, connected, status]);

  return (
    <aside className={`ollama-robot ollama-robot--${mode}`} aria-live="polite">
      <div className="ollama-robot__avatar" aria-hidden="true">
        <div className="ollama-robot__antenna">
          <span className="ollama-robot__antenna-bulb" />
        </div>
        <div className="ollama-robot__head">
          <div className="ollama-robot__eye ollama-robot__eye--l" />
          <div className="ollama-robot__eye ollama-robot__eye--r" />
          <div className="ollama-robot__mouth" />
        </div>
        <div className="ollama-robot__body">
          <Bot size={18} />
        </div>
        {working && <div className="ollama-robot__gears" />}
      </div>

      <div className="ollama-robot__copy">
        <div className="ollama-robot__title-row">
          <strong>{headline}</strong>
          <span className={`ollama-robot__badge ollama-robot__badge--${mode}`}>
            {mode === 'working' ? (
              <>
                <Cpu size={12} /> Trabajando
              </>
            ) : mode === 'idle' ? (
              <>
                <Wifi size={12} /> Online
              </>
            ) : (
              <>
                <WifiOff size={12} /> Offline
              </>
            )}
          </span>
        </div>
        <p className="ollama-robot__detail">{detail}</p>
        {working && progress != null && (
          <div className="ollama-robot__bar" title={`${progress}%`}>
            <div className="ollama-robot__bar-fill" style={{ width: `${progress}%` }} />
          </div>
        )}
        {working && (
          <p className="ollama-robot__eta">
            <Clock size={12} /> Estimación total ~{formatDuration(etaSec)} · orientativa
          </p>
        )}
        {!working && (
          <button type="button" className="ollama-robot__refresh" onClick={onRefresh}>
            Verificar Ollama
          </button>
        )}
      </div>
    </aside>
  );
}

export const JOB_META = {
  collect: { label: 'Recolectando feeds RSS', etaSec: 75, needsOllama: false },
  analyze: { label: 'Clasificando y verificando con Ollama', etaSec: 55, needsOllama: true },
  classify: { label: 'Clasificando lote con Ollama', etaSec: 840, needsOllama: true },
  multiformat: { label: 'Generando paquete multi-formato', etaSec: 480, needsOllama: true },
  'ai-test': { label: 'Probando conexión Ollama', etaSec: 30, needsOllama: true },
  search: { label: 'Buscando noticias en base de datos', etaSec: 4, needsOllama: false },
  agentic: { label: 'Patrulla web + evaluación Ollama', etaSec: 360, needsOllama: true },
  report: { label: 'Generando reporte semanal', etaSec: 120, needsOllama: true },
  'agents-run': { label: 'Agente editorial en curso', etaSec: 90, needsOllama: true },
  'agents-pipeline': { label: 'Pipeline de agentes editoriales', etaSec: 420, needsOllama: true },
};

function formatDuration(totalSec) {
  const s = Math.max(0, Math.round(Number(totalSec) || 0));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m < 60) return r ? `${m}m ${r}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm ? `${h}h ${rm}m` : `${h}h`;
}
