import { api } from './api';

const ACTIVE_JOBS_KEY = 'a360_active_jobs';
const TERMINAL = new Set(['completed', 'failed']);

export async function enqueueJob(path, {
  method = 'POST',
  body,
  idempotencyKey,
  label,
} = {}) {
  const separator = path.includes('?') ? '&' : '?';
  const job = await api(`${path}${separator}async_mode=true`, {
    method,
    body: body == null ? undefined : JSON.stringify(body),
    headers: {
      'Idempotency-Key': idempotencyKey || createIdempotencyKey(path),
    },
  });
  rememberJob({ ...job, label });
  return job;
}

export async function waitForJob(jobId, {
  intervalMs = 2500,
  timeoutMs = 30 * 60 * 1000,
  onUpdate,
  signal,
} = {}) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (signal?.aborted) throw new DOMException('Job tracking cancelled', 'AbortError');
    const job = await api(`/jobs/${jobId}`);
    rememberJob(job);
    onUpdate?.(job);
    if (TERMINAL.has(job.status)) {
      forgetJob(job.id);
      if (job.status === 'failed') {
        throw new Error(job.error_message || `El trabajo ${job.id} falló`);
      }
      return job;
    }
    await delay(intervalMs, signal);
  }
  throw new Error('El trabajo continúa en segundo plano. Puedes revisar su estado en Actividad.');
}

export function getRememberedJobs() {
  try {
    const raw = localStorage.getItem(ACTIVE_JOBS_KEY);
    const rows = raw ? JSON.parse(raw) : [];
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

function rememberJob(job) {
  if (!job?.id) return;
  try {
    const current = getRememberedJobs().filter((item) => item.id !== job.id);
    localStorage.setItem(
      ACTIVE_JOBS_KEY,
      JSON.stringify([{ ...job, remembered_at: Date.now() }, ...current].slice(0, 10))
    );
  } catch {
    // Persistencia de actividad es una mejora de UX, no bloquea el job.
  }
}

function forgetJob(jobId) {
  try {
    const next = getRememberedJobs().filter((item) => item.id !== jobId);
    localStorage.setItem(ACTIVE_JOBS_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

function createIdempotencyKey(path) {
  const safePath = path.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '');
  if (globalThis.crypto?.randomUUID) {
    return `${safePath}:${globalThis.crypto.randomUUID()}`;
  }
  return `${safePath}:${Date.now()}:${Math.random().toString(36).slice(2)}`;
}

function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timer);
        reject(new DOMException('Job tracking cancelled', 'AbortError'));
      },
      { once: true }
    );
  });
}

