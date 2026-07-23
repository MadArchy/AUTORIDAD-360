/** Normalizers de shapes API → UI (extraídos de App.jsx — Etapa 2). */

export function normalizeTop10(items) {
  return (items || []).map((it) => ({
    ...it,
    id: it.article_id ?? it.id,
    top10_score: Math.round(Number(it.total_score ?? 0)),
    verification_status: it.verification_status || 'verified',
    category: it.matched_pillar || it.category || 'editorial',
    content_full: it.summary || '',
    summary: typeof it.summary === 'string' ? it.summary : '',
    url: it.source_url,
    source_name: it.source_name || 'Fuente',
  }));
}

export function normalizeArticle(a) {
  return {
    ...a,
    verification_status: a.status || 'collected',
    url: a.source_url,
    category: a.category || 'sin-categoria',
  };
}

export function normalizeOpsSlot(slot) {
  const tasks = (slot.tasks || []).map((t) => ({
    ...t,
    task_name: t.task_name || t.title || t.task_type || 'Tarea',
    assignee: t.assignee || 'Sin asignar',
    status: t.status || 'todo',
  }));
  const risk = slot.risk || {};
  const riskReason =
    slot.risk_reason ||
    (Array.isArray(risk.reasons) && risk.reasons.length ? risk.reasons.join('; ') : null) ||
    (slot.piece_id ? 'Sin detalle de riesgo.' : 'Pieza no adjunta — adjunta contenido verificado.');
  return {
    ...slot,
    channel: slot.channel || slot.format_type || 'canal',
    format_type: slot.format_type || 'linkedin',
    scheduled_date: slot.scheduled_date || slot.scheduled_at,
    risk_level: slot.risk_level || 'yellow',
    risk_reason: riskReason,
    status: slot.status || 'planned',
    tasks,
  };
}
