import React, { useEffect, useState } from 'react';
import { CheckCircle2, Clock3, Cpu, RefreshCw, ServerOff } from 'lucide-react';

export default function ActivityCenter({ status, job, onRefresh }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!job?.startedAt) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [job?.startedAt]);

  const working = Boolean(job?.key);
  const connected = Boolean(status?.connected);
  const elapsed = job?.startedAt
    ? Math.max(0, Math.floor((now - job.startedAt) / 1000))
    : 0;

  return (
    <section
      className={`activity-center ${working ? 'is-working' : connected ? 'is-ready' : 'is-offline'}`}
      aria-live="polite"
      aria-label="Estado de procesamiento"
    >
      <div className="activity-icon" aria-hidden="true">
        {working ? (
          <Cpu size={18} />
        ) : connected ? (
          <CheckCircle2 size={18} />
        ) : (
          <ServerOff size={18} />
        )}
      </div>
      <div className="activity-copy">
        <strong>
          {working
            ? job.label || 'Procesando'
            : connected
              ? 'Motor editorial disponible'
              : 'Motor editorial sin conexión'}
        </strong>
        <span>
          {working
            ? `En curso · ${formatDuration(elapsed)}`
            : connected
              ? `${status?.model || 'Ollama local'} · ${status?.latency_ms ?? '—'} ms`
              : status?.error || 'Comprueba Ollama para las tareas de IA'}
        </span>
      </div>
      {working && (
        <span className="activity-elapsed">
          <Clock3 size={14} aria-hidden="true" />
          {formatDuration(elapsed)}
        </span>
      )}
      {!working && (
        <button
          type="button"
          className="activity-refresh"
          onClick={onRefresh}
          aria-label="Comprobar motor editorial"
        >
          <RefreshCw size={15} aria-hidden="true" />
        </button>
      )}
    </section>
  );
}

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return remaining ? `${minutes}m ${remaining}s` : `${minutes}m`;
}

