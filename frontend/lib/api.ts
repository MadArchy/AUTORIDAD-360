const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type BlogPost = {
  id: number;
  article_id: number;
  title: string;
  slug: string;
  content_html: string;
  source_url: string;
  source_citation: string;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  published_at: string | null;
  original_summary: string | null;
  original_full_text: string | null;
};

export type Top10Item = {
  rank: number;
  article_id: number;
  title: string;
  source_url: string;
  source_name: string;
  total_score: number;
  base_score?: number;
  quota_boost?: number;
  matched_pillar?: string | null;
  summary: string;
};

export type QuotaPillar = {
  pillar_id: number;
  slug: string;
  name: string;
  target_pct: number;
  actual_pct: number;
  deficit_pct: number;
  count: number;
  needs_boost: boolean;
};

export type ContentPiece = {
  id: number;
  package_id: number;
  article_id: number;
  parent_piece_id: number | null;
  format_type: string;
  language: string;
  title: string;
  body_text: string;
  body_json: Record<string, unknown> | null;
  source_url: string;
  status: string;
  version: number;
  factual_review: { passed?: boolean; unsupported_claims?: string[] } | null;
  brand_review: { passed?: boolean; issues?: string[] } | null;
  generation_mode?: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
};

export type ContentPackage = {
  id: number;
  article_id: number;
  profile_id: number | null;
  status: string;
  article_title: string | null;
  article_summary: string | null;
  source_url: string | null;
  pieces: ContentPiece[];
  created_at: string | null;
};

export type CalendarSlot = {
  id: number;
  profile_id: number;
  piece_id: number | null;
  format_type: string;
  title: string;
  scheduled_at: string | null;
  status: string;
  risk_level: string;
  risk: {
    level?: string;
    reasons?: string[];
    blockers?: string[];
    can_publish?: boolean;
  } | null;
  channel: string | null;
  notes: string | null;
  tasks?: EditorialTask[];
};

export type EditorialTask = {
  id: number;
  slot_id: number;
  piece_id: number | null;
  task_type: string;
  title: string;
  assignee: string | null;
  status: string;
  due_at: string | null;
  attachment_url: string | null;
  attachment_notes: string | null;
  completed_at: string | null;
  completed_by: string | null;
};

export type DecisionLog = {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  from_status: string | null;
  to_status: string | null;
  risk_level: string | null;
  actor: string;
  reason: string | null;
  version: number | null;
  created_at: string | null;
};

export type AIProvider = {
  id: number;
  name: string;
  provider_type: string;
  model_name: string;
  base_url: string | null;
  key_hint: string | null;
  has_api_key: boolean;
  is_local: boolean;
  is_active: boolean;
  monthly_budget_usd: number | null;
  daily_limit_requests: number | null;
  priority: number;
  last_tested_at: string | null;
  last_test_ok: boolean | null;
};

export type AIUsageSummary = {
  days: number;
  total_calls: number;
  local_calls: number;
  paid_calls: number;
  local_pct: number;
  paid_pct: number;
  estimated_cost_usd: number;
  by_task: Record<string, number>;
  has_litellm: boolean;
  routing: Record<string, string>;
};

export type OrgContext = {
  user: { id: number; email: string; full_name: string; is_superadmin: boolean };
  organization: { id: number; slug: string; name: string; org_type: string };
  role: string;
  profile_id: number | null;
};

export type OrgClient = {
  id: number;
  slug: string;
  full_name: string;
  title: string | null;
  organization_id: number | null;
};

export type OrgMember = {
  membership_id: number;
  user_id: number;
  email: string | null;
  full_name: string | null;
  role: string;
  profile_id: number | null;
};

export type Lead = {
  id: number;
  organization_id: number | null;
  profile_id: number;
  pillar_id: number | null;
  piece_id: number | null;
  source_channel: string;
  contact_name: string;
  contact_email: string | null;
  contact_company: string | null;
  status: string;
  is_qualified: boolean;
  notes: string | null;
  created_at: string | null;
  converted_at: string | null;
};

export type MetricsDashboard = {
  period_days: number;
  operational: {
    slots_total: number;
    slots_published: number;
    slots_pending_approval: number;
    pieces_pending: number;
    pieces_approved: number;
    avg_approval_hours: number | null;
    avg_risk_score: number | null;
    decisions_logged: number;
  };
  commercial: {
    funnel: Record<string, number>;
    qualified_leads: number;
    conversion_rate_pct: number;
  };
  editorial: {
    pillars: {
      pillar_id: number;
      slug: string;
      name: string;
      target_pct: number;
      qualified_leads: number;
      total_leads: number;
      likes: number;
      comments: number;
    }[];
    total_likes: number;
    total_comments: number;
  };
};

export type PercentageRecommendation = {
  id: number;
  profile_id: number;
  organization_id: number | null;
  status: string;
  rationale: string;
  evidence: { likes_ignored?: boolean; qualified_leads_total?: number } | null;
  changes: {
    pillar_slug: string | null;
    from_pct: number;
    to_pct: number;
    delta: number;
    qualified_leads: number;
  }[];
  min_qualified_leads: number;
  created_at: string | null;
  decided_by: string | null;
};

export type Profile = {
  id: number;
  slug: string;
  full_name: string;
  title: string | null;
  bio: string | null;
  services: string[];
  audiences: string[];
  pillars: { id: number; slug: string; name: string; description: string | null }[];
  editorial_percentages: {
    pillar_slug: string | null;
    pillar_name: string | null;
    target_pct: number;
  }[];
  market_percentages: { market_code: string; target_pct: number }[];
  quota: {
    month_total_pieces: number;
    pillars: {
      slug: string;
      target_pct: number;
      actual_pct: number;
      deficit_pct: number;
    }[];
  };
};

async function fetchApi<T>(
  path: string,
  options?: RequestInit,
  tenant?: { email?: string; orgSlug?: string }
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(tenant?.email ? { "X-User-Email": tenant.email } : {}),
      ...(tenant?.orgSlug ? { "X-Org-Slug": tenant.orgSlug } : {}),
      ...options?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  getPendingPosts: () => fetchApi<BlogPost[]>("/api/v1/blog/pending"),
  getPublishedPosts: () => fetchApi<BlogPost[]>("/api/v1/blog/published"),
  getPost: (slug: string) => fetchApi<BlogPost>(`/api/v1/blog/${slug}`),
  getTop10: () => fetchApi<Top10Item[]>("/api/v1/top10"),
  getProfile: () => fetchApi<Profile>("/api/v1/profile"),
  getQuota: () =>
    fetchApi<{
      month_total_pieces: number;
      pillars: QuotaPillar[];
      markets: { market_code: string; target_pct: number }[];
    }>("/api/v1/profile/quota"),
  approvePost: (id: number, approvedBy: string) =>
    fetchApi<BlogPost>(`/api/v1/blog/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  rejectPost: (id: number, approvedBy: string, reason: string) =>
    fetchApi<BlogPost>(`/api/v1/blog/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy, reason }),
    }),
  publishPost: (id: number, approvedBy: string) =>
    fetchApi<BlogPost>(`/api/v1/blog/${id}/publish`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  createDraft: (articleId: number) =>
    fetchApi<BlogPost>(`/api/v1/blog/from-article/${articleId}`, { method: "POST" }),
  triggerCollect: () => fetchApi("/api/v1/jobs/collect", { method: "POST" }),
  triggerClassify: () => fetchApi("/api/v1/jobs/classify", { method: "POST" }),
  triggerReport: () => fetchApi("/api/v1/jobs/report", { method: "POST" }),
  getContentPackages: () => fetchApi<ContentPackage[]>("/api/v1/content/packages"),
  getPendingContent: () => fetchApi<ContentPiece[]>("/api/v1/content/pending"),
  generateContentPackage: (articleId: number, preferLlm = false) =>
    fetchApi<ContentPackage>(`/api/v1/content/from-article/${articleId}`, {
      method: "POST",
      body: JSON.stringify({ languages: ["es"], prefer_llm: preferLlm }),
    }),
  approveContentPiece: (id: number, approvedBy: string) =>
    fetchApi<ContentPiece>(`/api/v1/content/pieces/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  rejectContentPiece: (id: number, approvedBy: string, reason: string) =>
    fetchApi<ContentPiece>(`/api/v1/content/pieces/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy, reason }),
    }),
  reuseContentPiece: (id: number) =>
    fetchApi<{ created: number; pieces: ContentPiece[] }>(
      `/api/v1/content/pieces/${id}/reuse?prefer_llm=false`,
      { method: "POST" }
    ),
  getCalendar: (days = 30) => fetchApi<CalendarSlot[]>(`/api/v1/ops/calendar?days=${days}`),
  getSlot: (id: number) => fetchApi<CalendarSlot>(`/api/v1/ops/calendar/${id}`),
  generateCalendar: (weeks = 2) =>
    fetchApi<{ created: number; slots: CalendarSlot[] }>("/api/v1/ops/calendar/generate", {
      method: "POST",
      body: JSON.stringify({ weeks }),
    }),
  attachPiece: (slotId: number, pieceId: number, actor: string) =>
    fetchApi<CalendarSlot>(`/api/v1/ops/calendar/${slotId}/attach`, {
      method: "POST",
      body: JSON.stringify({ actor, piece_id: pieceId }),
    }),
  advanceSlot: (
    slotId: number,
    targetStatus: string,
    actor: string,
    reason?: string,
    riskOverride = false
  ) =>
    fetchApi<CalendarSlot>(`/api/v1/ops/calendar/${slotId}/advance`, {
      method: "POST",
      body: JSON.stringify({
        actor,
        target_status: targetStatus,
        reason,
        risk_override: riskOverride,
      }),
    }),
  getTasks: (status?: string) =>
    fetchApi<EditorialTask[]>(
      status ? `/api/v1/ops/tasks?status=${status}` : "/api/v1/ops/tasks"
    ),
  updateTask: (
    id: number,
    body: {
      actor: string;
      status?: string;
      assignee?: string;
      attachment_url?: string;
      attachment_notes?: string;
    }
  ) =>
    fetchApi<EditorialTask>(`/api/v1/ops/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  getDecisions: (limit = 50) =>
    fetchApi<DecisionLog[]>(`/api/v1/ops/decisions?limit=${limit}`),
  getAIProviders: () => fetchApi<AIProvider[]>("/api/v1/ai/providers"),
  createAIProvider: (body: {
    name: string;
    provider_type: string;
    model_name: string;
    api_key?: string;
    monthly_budget_usd?: number;
    daily_limit_requests?: number;
  }) =>
    fetchApi<AIProvider>("/api/v1/ai/providers", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  testAIProvider: (id: number) =>
    fetchApi<{ ok: boolean; latency_ms?: number; error?: string; has_litellm?: boolean; sample?: string }>(
      `/api/v1/ai/providers/${id}/test`,
      { method: "POST" }
    ),
  getAIUsage: (days = 30) => fetchApi<AIUsageSummary>(`/api/v1/ai/usage?days=${days}`),
  seedOrgs: () => fetchApi("/api/v1/orgs/seed", { method: "POST" }),
  getOrgMe: (tenant: { email: string; orgSlug: string }) =>
    fetchApi<OrgContext>("/api/v1/orgs/me", undefined, tenant),
  getOrgClients: (tenant: { email: string; orgSlug: string }) =>
    fetchApi<OrgClient[]>("/api/v1/orgs/clients", undefined, tenant),
  getOrgMembers: (tenant: { email: string; orgSlug: string }) =>
    fetchApi<OrgMember[]>("/api/v1/orgs/members", undefined, tenant),
  onboardClient: (
    body: { slug: string; full_name: string; title?: string; email: string },
    tenant: { email: string; orgSlug: string }
  ) =>
    fetchApi("/api/v1/orgs/clients/onboard", {
      method: "POST",
      body: JSON.stringify(body),
    }, tenant),
  getMetricsDashboard: (days = 30) =>
    fetchApi<MetricsDashboard>(`/api/v1/metrics/dashboard?days=${days}`),
  getLeads: () => fetchApi<Lead[]>("/api/v1/leads"),
  createLead: (body: {
    contact_name: string;
    contact_email?: string;
    pillar_id?: number;
    status?: string;
    is_qualified?: boolean;
  }) =>
    fetchApi<Lead>("/api/v1/leads", { method: "POST", body: JSON.stringify(body) }),
  generatePercentageRec: () =>
    fetchApi<{ recommendation: PercentageRecommendation | null; message?: string }>(
      "/api/v1/recommendations/percentages/generate",
      { method: "POST" }
    ),
  getPercentageRecs: (status = "pending") =>
    fetchApi<PercentageRecommendation[]>(
      `/api/v1/recommendations/percentages?status=${status}`
    ),
  decidePercentageRec: (id: number, actor: string, accept: boolean, reason?: string) =>
    fetchApi<PercentageRecommendation>(`/api/v1/recommendations/percentages/${id}/decide`, {
      method: "POST",
      body: JSON.stringify({ actor, accept, reason }),
    }),
};
