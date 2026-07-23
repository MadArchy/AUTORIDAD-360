import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  ShieldCheck, 
  Newspaper, 
  CheckCircle2, 
  XCircle, 
  ExternalLink, 
  RefreshCw, 
  FileText, 
  BarChart2, 
  Search, 
  BookOpen,
  Send,
  Sparkles,
  Layers,
  User,
  Sliders,
  Video,
  Linkedin,
  Mail,
  Copy,
  Calendar,
  AlertTriangle,
  CheckSquare,
  Clock,
  History,
  Cpu,
  Zap,
  DollarSign,
  Activity,
  Building2,
  Users,
  Target,
  TrendingUp,
  PieChart,
  UserPlus,
  Globe,
  Filter,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Bot,
  LogOut
} from 'lucide-react';
import {
  api,
  normalizePackage,
  normalizeCarouselSlides,
  normalizeProfile,
  normalizeReport,
  normalizeUsage,
  normalizeDashboard,
  isAuthenticated,
  getStoredUser,
  logout,
  getHealth,
} from './api';
import { JOB_META } from './OllamaRobot';
import AppShell from './components/AppShell';
import ActivityCenter from './components/ActivityCenter';
import LoginScreen from './LoginScreen';
import Top10Tab from './tabs/Top10Tab';
import AIGatewayTab from './tabs/AIGatewayTab';
import AgentsTab from './tabs/AgentsTab';
import OpsCalendarTab from './tabs/OpsCalendarTab';
import LiveNewsTab from './tabs/LiveNewsTab';
import MultiFormatTab from './tabs/MultiFormatTab';
import ProfileTab from './tabs/ProfileTab';
import ApprovalTab from './tabs/ApprovalTab';
import BlogTab from './tabs/BlogTab';
import PublishTab from './tabs/PublishTab';
import LegalSeoTab from './tabs/LegalSeoTab';
import MarketingTab from './tabs/MarketingTab';
import RefreshTab from './tabs/RefreshTab';
import ReportTab from './tabs/ReportTab';
import MultiEmpresaTab from './tabs/MultiEmpresaTab';
import MetricsTab from './tabs/MetricsTab';
import HoyTab from './tabs/HoyTab';
import { normalizeTop10, normalizeArticle, normalizeOpsSlot } from './utils/normalizers';
import { enqueueJob, getRememberedJobs, waitForJob } from './jobs';

export default function App() {
  const [authUser, setAuthUser] = useState(() => (isAuthenticated() ? getStoredUser() : null));
  const [healthInfo, setHealthInfo] = useState(null);
  const [activeTab, setActiveTab] = useState('hoy');
  const [articles, setArticles] = useState([]);
  const [top10, setTop10] = useState([]);
  const [categories, setCategories] = useState([]);
  const [profile, setProfile] = useState(null);
  const [report, setReport] = useState(null);
  const [multiFormatContent, setMultiFormatContent] = useState(null);
  const [calendarSlots, setCalendarSlots] = useState([]);
  const [decisionLogs, setDecisionLogs] = useState([]);
  const [aiProviders, setAiProviders] = useState([]);
  const [aiUsageStats, setAiUsageStats] = useState(null);
  const [testPrompt, setTestPrompt] = useState('Analiza las implicaciones legales y de gobernanza de la IA generativa.');
  const [testResult, setTestResult] = useState(null);
  const [selectedFormatSubTab, setSelectedFormatSubTab] = useState('linkedin');
  const [selectedLanguage, setSelectedLanguage] = useState('es');
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState({});
  const [toasts, setToasts] = useState([]);
  const [robotJob, setRobotJob] = useState(null);
  const [formatGenBanner, setFormatGenBanner] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [articlesTotalHint, setArticlesTotalHint] = useState(null);
  const searchDebounceRef = useRef(null);
  const [selectedArticleForApproval, setSelectedArticleForApproval] = useState(null);
  const [approvedArticleIds, setApprovedArticleIds] = useState(new Set());

  // Fase 6 — Multiempresa
  const [orgs, setOrgs] = useState([]);
  const [orgMembers, setOrgMembers] = useState([]);
  const [orgClients, setOrgClients] = useState([]);
  const [orgRoles, setOrgRoles] = useState([]);
  const [orgContext, setOrgContext] = useState(null);
  const [newMember, setNewMember] = useState({ email: '', full_name: '', role: 'writer' });
  const [newClient, setNewClient] = useState({ slug: '', full_name: '', title: '', email: '', bio: '' });

  // Fase 7 — Métricas, Leads, Aprendizaje
  const [leads, setLeads] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [newLead, setNewLead] = useState({
    contact_name: '',
    contact_email: '',
    contact_company: '',
    source_channel: 'linkedin',
    notes: '',
    pillar_id: '',
    piece_id: '',
    utm_source: '',
    utm_medium: '',
    utm_campaign: '',
    service_offer_id: '',
    landing_url: '',
  });
  const [leadFilter, setLeadFilter] = useState('');
  const [newProvider, setNewProvider] = useState({
    name: '',
    provider_type: 'openai',
    model_name: '',
    api_key: '',
    base_url: '',
    monthly_budget_usd: '',
    priority: 50,
  });
  const [pendingBlogPosts, setPendingBlogPosts] = useState([]);
  const [publishedBlogPosts, setPublishedBlogPosts] = useState([]);
  const [pillarDrafts, setPillarDrafts] = useState({});
  const [multiFormatError, setMultiFormatError] = useState('');
  const [reportError, setReportError] = useState('');
  const [contentPackages, setContentPackages] = useState([]);
  const [pilotTick, setPilotTick] = useState(0);
  const [agentsCatalog, setAgentsCatalog] = useState(null);
  const [agentRunResult, setAgentRunResult] = useState(null);
  const [agentArticleId, setAgentArticleId] = useState('');
  const [agentPipelineMode, setAgentPipelineMode] = useState('ingest');
  const [agentLimit, setAgentLimit] = useState(3);
  const [agentReason, setAgentReason] = useState(false);

  const notify = (message, type = 'info') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const text = String(message || '').slice(0, 500);
    setToasts((prev) => [...prev.slice(-4), { id, message: text, type }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4200);
  };

  const withBusy = async (key, fn, meta = null) => {
    const info = meta || JOB_META[key] || { label: 'Procesando…', etaSec: 30 };
    if (info.needsOllama && ollamaStatus && !ollamaStatus.connected) {
      notify('Ollama está offline. El robot lo marca en rojo; arranca Ollama para tareas de IA.', 'warn');
    }
    setBusy((b) => ({ ...b, [key]: true }));
    setRobotJob({
      key,
      label: info.label,
      etaSec: info.etaSec,
      needsOllama: Boolean(info.needsOllama),
      startedAt: Date.now(),
    });
    if (!info.background) setLoading(true);
    try {
      return await fn();
    } finally {
      setBusy((b) => {
        const next = { ...b };
        delete next[key];
        return next;
      });
      setRobotJob(null);
      if (!info.background) setLoading(false);
      if (info.needsOllama) checkOllamaStatus();
    }
  };

  const isBusy = (key) => Boolean(busy[key]);

  const runBackgroundJob = async (path, {
    body,
    key,
    label,
    timeoutMs,
  }) => {
    const job = await enqueueJob(path, { body, label });
    setRobotJob((current) => ({
      ...(current || {}),
      key,
      label,
      jobId: job.id,
      status: job.status,
      startedAt: current?.startedAt || Date.now(),
    }));
    return waitForJob(job.id, {
      timeoutMs,
      onUpdate: (update) => {
        setRobotJob((current) => ({
          ...(current || {}),
          key,
          label,
          jobId: update.id,
          status: update.status,
          startedAt: current?.startedAt || Date.now(),
        }));
      },
    });
  };

  const checkOllamaStatus = async () => {
    try {
      const data = await api('/ai/ollama/status');
      setOllamaStatus(data);
      return data;
    } catch (e) {
      setOllamaStatus({
        connected: false,
        model: 'desconocido',
        error: e.message || 'No se pudo consultar estado de Ollama',
      });
      return null;
    }
  };

  useEffect(() => {
    if (!authUser) return undefined;
    checkOllamaStatus();
    const id = window.setInterval(checkOllamaStatus, 15000);
    return () => window.clearInterval(id);
  }, [authUser]);

  useEffect(() => {
    if (!authUser) return;
    getHealth()
      .then(setHealthInfo)
      .catch(() => setHealthInfo({ status: 'error' }));
  }, [authUser]);

  // Initial Data Fetching — núcleo + fuentes del progreso del ciclo
  useEffect(() => {
    if (!authUser) return;
    fetchCategories();
    fetchTop10();
    fetchArticles();
    fetchProfile();
    refreshPilotSources();
  }, [authUser]);

  useEffect(() => {
    if (!authUser) return undefined;
    const pending = getRememberedJobs().find(
      (job) => !['completed', 'failed'].includes(job.status)
    );
    if (!pending) return undefined;
    const controller = new AbortController();
    const label = pending.label || 'Retomando trabajo editorial';
    setRobotJob({
      key: pending.job_name || 'background',
      label,
      jobId: pending.id,
      status: pending.status,
      startedAt: pending.remembered_at || Date.now(),
    });
    waitForJob(pending.id, {
      signal: controller.signal,
      onUpdate: (job) => {
        setRobotJob((current) => ({ ...current, status: job.status }));
      },
    })
      .then(() => {
        setRobotJob(null);
        refreshPilotSources();
        notify(`${label}: completado`, 'success');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setRobotJob(null);
          notify(error.message || 'No se pudo recuperar el trabajo', 'error');
        }
      });
    return () => controller.abort();
  }, [authUser]);

  const refreshPilotSources = async () => {
    try {
      const [slotsData, logsData, blogs, pending, leadsData, packages] = await Promise.all([
        api('/ops/calendar').catch(() => []),
        api('/ops/decisions').catch(() => []),
        api('/blog/published').catch(() => []),
        api('/blog/pending').catch(() => []),
        api('/leads?limit=50').catch(() => []),
        api('/content/packages?limit=20').catch(() => []),
      ]);
      setCalendarSlots((slotsData || []).map(normalizeOpsSlot));
      setDecisionLogs(logsData || []);
      setPublishedBlogPosts(blogs || []);
      setPendingBlogPosts(pending || []);
      setLeads(leadsData || []);
      setContentPackages(packages || []);
      setPilotTick((n) => n + 1);
    } catch (e) {
      console.error('Error refreshing pilot progress', e);
    }
  };

  const goToTab = (tab) => {
    setActiveTab(tab);
    if (tab === 'ops') fetchOpsData();
    if (tab === 'aigateway') fetchAiStats();
    if (tab === 'agents') fetchAgentsCatalog();
    if (tab === 'profile') fetchProfile();
    if (tab === 'report') fetchReport();
    if (tab === 'multiempresa') fetchOrgData();
    if (tab === 'metrics') fetchMetricsData();
    if (tab === 'blog' || tab === 'publish') {
      fetchPendingBlogs();
      fetchPublishedBlogs();
    }
    if (tab === 'live') fetchArticles();
    if (['ops', 'blog', 'metrics', 'multiformat', 'approval', 'top10'].includes(tab)) {
      // progreso se recalcula con el estado; refrescar fuentes en pasos clave
      if (tab === 'ops' || tab === 'blog' || tab === 'metrics') refreshPilotSources();
    }
  };

  const useArticleInFlow = (art) => {
    const normalized = normalizeArticle(art);
    const title = (art.title || '').toLowerCase();
    if (
      title.includes('shipping') ||
      title.includes('incoterm') ||
      title.includes('global business navigator') ||
      title.includes('acd_test')
    ) {
      notify(
        'Esa noticia está fuera de tipología (comercio genérico). Elige otra del Top 10 con ángulo IA/regulación/legal.',
        'warn'
      );
    }
    setMultiFormatContent(null);
    setSelectedArticleForApproval({
      ...normalized,
      id: art.id,
      content_full: art.summary || art.content_full || '',
      summary: art.summary || '',
      url: art.source_url || art.url,
    });
    setActiveTab('multiformat');
    fetchMultiFormat(art.id, selectedLanguage, { showBanner: true, clearContent: true });
  };

  const packagePieces = useMemo(
    () => (contentPackages || []).flatMap((p) => p.pieces || []),
    [contentPackages, pilotTick]
  );
  const livePieces = useMemo(
    () => multiFormatContent?.pieces || [],
    [multiFormatContent]
  );
  const allPieces = useMemo(
    () => [...packagePieces, ...livePieces],
    [packagePieces, livePieces]
  );

  const pilotProgress = useMemo(() => {
    const hasNews = (top10 || []).length > 0;
    const hasFormats = allPieces.length > 0 || (contentPackages || []).length > 0;
    const hasApprovedPiece =
      allPieces.some((p) => p.status === 'approved') ||
      approvedArticleIds.size > 0 ||
      (pendingBlogPosts || []).some((p) => p.status === 'approved');
    const hasPublished =
      (publishedBlogPosts || []).length > 0 ||
      (calendarSlots || []).some((s) => s.status === 'published');
    return {
      top10: hasNews,
      multiformat: hasFormats,
      approval: hasApprovedPiece,
      publish: hasPublished,
    };
  }, [
    top10,
    allPieces,
    contentPackages,
    approvedArticleIds,
    pendingBlogPosts,
    calendarSlots,
    publishedBlogPosts,
    pilotTick,
  ]);

  const PILOT_STEPS = [
    {
      id: 'top10',
      label: 'Elegir',
      tab: 'top10',
      hint: 'Elige una noticia del Top 10',
      cta: 'Abrir Top 10',
    },
    {
      id: 'multiformat',
      label: 'Generar',
      tab: 'top10',
      hint: 'Al usar una noticia del Top 10 se generan los formatos',
      cta: 'Ir a Elegir',
    },
    {
      id: 'approval',
      label: 'Aprobar',
      tab: 'approval',
      hint: 'Revisa y aprueba la pieza o el blog',
      cta: 'Ir a aprobar',
    },
    {
      id: 'publish',
      label: 'Publicar',
      tab: 'publish',
      hint: 'Crea el paquete de canales y confirma',
      cta: 'Ir a publicar',
    },
  ];
  const pilotDoneCount = PILOT_STEPS.filter((s) => pilotProgress[s.id]).length;
  const nextPilotStep = PILOT_STEPS.find((s) => !pilotProgress[s.id]) || null;

  const fetchCategories = async () => {
    try {
      const data = await api('/articles?limit=100');
      const counts = {};
      for (const a of data || []) {
        const key = a.category || 'sin-categoria';
        counts[key] = (counts[key] || 0) + 1;
      }
      setCategories(
        Object.entries(counts).map(([category, count]) => ({
          category,
          display_name: category,
          count,
        }))
      );
    } catch (e) {
      console.error("Error loading categories", e);
    }
  };

  const fetchProfile = async () => {
    try {
      const data = normalizeProfile(await api('/profile'));
      setProfile(data);
      const drafts = {};
      for (const p of data?.pillars || []) drafts[p.slug] = p.target_percentage;
      setPillarDrafts(drafts);
    } catch (e) {
      console.error("Error fetching profile", e);
    }
  };

  const saveProfilePercentages = async () => {
    if (!profile) return;
    try {
      const editorial = (profile.pillars || []).map((p) => ({
        pillar_slug: p.slug,
        target_pct: Number(pillarDrafts[p.slug] ?? p.target_percentage ?? 0),
      }));
      const markets = (profile.markets || []).map((m) => ({
        market_code: m.market_code,
        target_pct: Number(m.target_percentage),
      }));
      const sum = editorial.reduce((a, b) => a + b.target_pct, 0);
      if (Math.abs(sum - 100) > 0.5) {
        notify(`Los pilares deben sumar 100% (ahora ${sum}%).`);
        return;
      }
      const data = normalizeProfile(
        await api('/profile/percentages', {
          method: 'PUT',
          body: JSON.stringify({ editorial, markets }),
        })
      );
      setProfile(data);
      notify('Porcentajes editoriales guardados.');
    } catch (e) {
      notify(e.message || 'Error al guardar porcentajes');
    }
  };

  const fetchOpsData = async () => {
    setLoading(true);
    try {
      const [slotsData, logsData] = await Promise.all([
        api('/ops/calendar'),
        api('/ops/decisions'),
      ]);
      setCalendarSlots((slotsData || []).map(normalizeOpsSlot));
      setDecisionLogs(logsData || []);
    } catch (e) {
      console.error("Error fetching ops data", e);
      setCalendarSlots([]);
      setDecisionLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAiStats = async () => {
    setLoading(true);
    try {
      const [pData, uData] = await Promise.all([
        api('/ai/providers'),
        api('/ai/usage'),
      ]);
      setAiProviders(pData || []);
      setAiUsageStats(normalizeUsage(uData));
    } catch (e) {
      console.error("Error fetching AI stats", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgentsCatalog = async () => {
    try {
      const data = await api('/agents');
      setAgentsCatalog(data || { agents: [] });
    } catch (e) {
      console.error(e);
      setAgentsCatalog({ agents: [], error: e.message });
      notify(e.message || 'Error al cargar agentes', 'error');
    }
  };

  const runNamedAgent = async (name) => {
    const articleId = agentArticleId ? Number(agentArticleId) : null;
    const needsArticle = name === 'writer' || name === 'verifier';
    if (needsArticle && !Number.isFinite(articleId)) {
      notify(`${name} necesita un article_id (noticia verificada)`, 'warn');
      return;
    }
    await withBusy('agents-run', async () => {
      try {
        const result = await api(`/agents/${name}/run`, {
          method: 'POST',
          body: JSON.stringify({
            article_id: Number.isFinite(articleId) ? articleId : null,
            limit: agentLimit,
            languages: ['es'],
            prefer_llm: true,
            reason: agentReason,
          }),
        });
        setAgentRunResult(result);
        const batchErrors = result?.artifacts?.batch?.errors?.length
          || result?.steps?.some((s) => s.status === 'error');
        if (result.ok && !batchErrors) {
          notify(`Agente ${name} OK (${result.duration_ms || 0} ms)`, 'success');
        } else if (result.ok && batchErrors) {
          notify(`Agente ${name} terminó con avisos — revisa el JSON`, 'warn');
        } else {
          notify(result.summary || `Agente ${name} con errores`, 'warn');
        }
      } catch (e) {
        notify(e.message || `Error en agente ${name}`, 'error');
      }
    });
  };

  const runAgentsPipeline = async () => {
    const articleId = agentArticleId ? Number(agentArticleId) : null;
    if (agentPipelineMode === 'article' && !Number.isFinite(articleId)) {
      notify('El modo article requiere un article_id', 'warn');
      return;
    }
    await withBusy('agents-pipeline', async () => {
      try {
        const result = await api('/agents/pipeline/run', {
          method: 'POST',
          body: JSON.stringify({
            mode: agentPipelineMode,
            article_id: Number.isFinite(articleId) ? articleId : null,
            limit: agentLimit,
            languages: ['es'],
            prefer_llm: true,
            reason: agentReason,
          }),
        });
        setAgentRunResult(result);
        notify(
          result.ok
            ? `Pipeline ${agentPipelineMode} OK (${Math.round((result.duration_ms || 0) / 1000)}s)`
            : `Pipeline ${agentPipelineMode}: ${result.summary || 'con errores'}`,
          result.ok ? 'success' : 'warn'
        );
        refreshPilotSources();
      } catch (e) {
        notify(e.message || 'Error en pipeline de agentes', 'error');
      }
    });
  };

  const runAgenticSearch = async () => {
    await withBusy('agentic', async () => {
      setIsSearching(true);
      try {
        const body = {
          max_results_per_query: 2,
          max_queries: 12,
          max_priority: 11,
          queries: searchQuery.trim() ? [searchQuery.trim()] : null,
        };
        const res = await api('/ops/search/run', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        const byType = res.stats?.by_news_type || {};
        const typeSummary = Object.entries(byType)
          .map(([k, v]) => `${k}:${v}`)
          .slice(0, 6)
          .join(' · ');
        notify(
          `Patrulla tipologías: ${res.stats?.saved_to_db || 0} nuevas · rechazadas ${res.stats?.rejected_low_relevance || 0} · ${res.stats?.urls_found || 0} URLs${typeSummary ? ` · ${typeSummary}` : ''}`,
          'success'
        );
        fetchCategories();
        fetchTop10();
        fetchArticles();
      } catch (e) {
        console.error(e);
        notify('Error en Búsqueda Agentica: ' + e.message, 'error');
      } finally {
        setIsSearching(false);
      }
    });
  };

  const createAiProvider = async () => {
    if (!newProvider.name || !newProvider.model_name) {
      return notify('Nombre y modelo son requeridos');
    }
    try {
      const body = {
        name: newProvider.name,
        provider_type: newProvider.provider_type,
        model_name: newProvider.model_name,
        api_key: newProvider.provider_type === 'ollama' ? null : newProvider.api_key || null,
        base_url: newProvider.base_url || null,
        monthly_budget_usd: newProvider.monthly_budget_usd
          ? Number(newProvider.monthly_budget_usd)
          : null,
        priority: Number(newProvider.priority) || 50,
      };
      await api('/ai/providers', { method: 'POST', body: JSON.stringify(body) });
      notify('Proveedor agregado. La API key queda cifrada.');
      setNewProvider({
        name: '',
        provider_type: 'openai',
        model_name: '',
        api_key: '',
        base_url: '',
        monthly_budget_usd: '',
        priority: 50,
      });
      fetchAiStats();
    } catch (e) {
      notify(e.message || 'Error al crear proveedor');
    }
  };

  const runGatewayTest = async () => {
    await withBusy('ai-test', async () => {
      try {
        const providers = await api('/ai/providers');
        const local = (providers || []).find((p) => p.is_local) || providers?.[0];
        if (!local) throw new Error('Sin proveedores');
        const data = await api(`/ai/providers/${local.id}/test`, {
          method: 'POST',
          body: JSON.stringify({ prompt: testPrompt }),
        });
        setTestResult({
          ...data,
          prompt: testPrompt,
          provider: local.name,
          text: data.text || data.response_preview || data.error || '',
          model: data.model || local.model_name,
          fallback_triggered: Boolean(data.fallback_triggered),
          total_tokens: data.total_tokens ?? 0,
          latency_ms: data.latency_ms ?? 0,
          estimated_cost_usd: data.estimated_cost_usd ?? 0,
        });
        fetchAiStats();
        notify(data.ok ? 'Prueba de gateway OK' : (data.error || 'Prueba fallida'), data.ok ? 'success' : 'error');
      } catch (e) {
        notify(e.message || 'Error al probar AI Gateway', 'error');
      }
    });
  };

  const fetchTop10 = async () => {
    setLoading(true);
    try {
      const data = normalizeTop10(await api('/top10'));
      setTop10(data);
      // Solo seleccionar #1; NO auto-generar LinkedIn (eso repetía siempre el mismo post)
      if (data.length > 0 && !selectedArticleForApproval) {
        setSelectedArticleForApproval(data[0]);
      }
    } catch (e) {
      console.error("Error fetching Top 10", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchArticles = async (cat = selectedCategory, search = searchQuery) => {
    const key = 'search';
    const info = JOB_META.search;
    setBusy((b) => ({ ...b, [key]: true }));
    setRobotJob({
      key,
      label: search?.trim() ? `Buscando “${search.trim()}”` : info.label,
      etaSec: info.etaSec,
      needsOllama: false,
      startedAt: Date.now(),
    });
    try {
      const params = new URLSearchParams();
      params.set('limit', search || cat ? '100' : '80');
      if (cat) params.set('category', cat);
      if (search && search.trim()) params.set('q', search.trim());
      const rows = (await api(`/articles?${params.toString()}`)).map(normalizeArticle);
      setArticles(rows);
      setArticlesTotalHint(rows.length);
      if (search && search.trim() && rows.length === 0) {
        notify(`Sin resultados para “${search.trim()}”. Prueba otra palabra o limpia el filtro.`, 'warn');
      }
    } catch (e) {
      console.error("Error fetching articles", e);
      notify(e.message || 'Error al buscar noticias', 'error');
    } finally {
      setBusy((b) => {
        const next = { ...b };
        delete next[key];
        return next;
      });
      setRobotJob(null);
    }
  };

  const onSearchInput = (value) => {
    setSearchQuery(value);
    if (searchDebounceRef.current) window.clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = window.setTimeout(() => {
      fetchArticles(selectedCategory, value);
    }, 350);
  };

  const fetchMultiFormat = async (articleId, lang = selectedLanguage, options = {}) => {
    const { clearContent = true, showBanner = false } = options;
    const langLabel = lang === 'en' ? 'inglés' : 'español';
    if (showBanner) setFormatGenBanner(true);
    try {
      await withBusy(
        'multiformat',
        async () => {
          setMultiFormatError('');
          if (clearContent) setMultiFormatContent(null);
          try {
            const job = await runBackgroundJob(`/content/from-article/${articleId}`, {
              key: 'multiformat',
              label: `Generando formatos en ${langLabel}`,
              body: { languages: [lang], prefer_llm: true },
              timeoutMs: 30 * 60 * 1000,
            });
            const packageId = job.result_json?.package_id;
            if (!packageId) throw new Error('El job terminó sin identificar el paquete');
            const data = normalizePackage(
              await api(`/content/packages/${packageId}`),
              lang
            );
            setMultiFormatContent(data);
            setSelectedLanguage(lang);
            const modes = (data.pieces || []).map((p) => p.generation_mode).filter(Boolean);
            const det = modes.filter((m) => m === 'deterministic').length;
            if (det > 0) {
              notify(
                `Paquete en ${langLabel} listo, pero ${det} pieza(s) usaron plantilla. Reintenta si el idioma no cuadra.`,
                'warn'
              );
            } else {
              notify(`Paquete multi-formato listo en ${langLabel}`, 'success');
            }
            refreshPilotSources();
          } catch (e) {
            console.error('Error fetching multi-format content', e);
            setMultiFormatError(e.message || 'Error al generar multi-formato');
            notify(e.message || 'Error al generar multi-formato', 'error');
          }
        },
        {
          ...JOB_META.multiformat,
          background: true,
          label: `Generando formatos en ${langLabel}`,
        }
      );
    } finally {
      if (showBanner) setFormatGenBanner(false);
    }
  };

  const changeFormatLanguage = (lang) => {
    if (!selectedArticleForApproval?.id) {
      setSelectedLanguage(lang);
      return;
    }
    if (lang === selectedLanguage && multiFormatContent) return;
    setSelectedLanguage(lang);
    fetchMultiFormat(selectedArticleForApproval.id, lang, {
      clearContent: false,
      showBanner: true,
    });
  };

  const triggerIngest = async () => {
    await withBusy('collect', async () => {
      try {
        await runBackgroundJob('/jobs/collect', {
          key: 'collect',
          label: 'Actualizando fuentes de noticias',
          timeoutMs: 15 * 60 * 1000,
        });
        notify('Fuentes actualizadas correctamente.', 'success');
        fetchCategories();
        fetchTop10();
        fetchArticles();
        fetchProfile();
      } catch (e) {
        notify(e.message || 'Error al ejecutar recolección RSS', 'error');
      }
    }, { ...JOB_META.collect, background: true });
  };

  const triggerAnalyzeArticle = async (articleId) => {
    await withBusy('analyze', async () => {
      try {
        const job = await runBackgroundJob(`/articles/${articleId}/analyze`, {
          key: 'analyze',
          label: 'Clasificando y verificando artículo',
          timeoutMs: 10 * 60 * 1000,
        });
        const result = job.result_json || {};
        const ok = result.status === 'verified' || result.publishable;
        notify(ok ? 'Análisis completado: VERIFICADO' : 'Análisis completado: requiere revisión', ok ? 'success' : 'warn');
        fetchTop10();
        fetchArticles();
      } catch (e) {
        notify(e.message || 'Error al analizar artículo', 'error');
      }
    }, { ...JOB_META.analyze, background: true });
  };

  const approveSlot = async (slotId, riskOverride = false) => {
    try {
      await api(`/ops/calendar/${slotId}/advance`, {
        method: 'POST',
        body: JSON.stringify({
          actor: 'Juan Vásquez',
          target_status: 'approved',
          reason: riskOverride
            ? 'Aprobación con override de riesgo explícito desde panel operativo.'
            : 'Aprobación efectuada desde el panel operativo tras validar semáforo de riesgo.',
          risk_override: riskOverride,
        }),
      });
      let packageNote = '';
      try {
        const pkg = await api(`/publish/from-slot/${slotId}`, {
          method: 'POST',
          body: JSON.stringify({}),
        });
        await api(`/ops/calendar/${slotId}/advance`, {
          method: 'POST',
          body: JSON.stringify({
            actor: 'Juan Vásquez',
            target_status: 'scheduled',
            reason: 'Paquete multi-canal creado; jobs programados con fecha del slot.',
            risk_override: riskOverride,
          }),
        });
        packageNote = ` Paquete #${pkg.id} listo en Canales.`;
      } catch (pubErr) {
        packageNote = ` (Aprobado; publicar desde Canales: ${pubErr.message || 'sin pieza'})`;
      }
      notify(`Slot #${slotId} aprobado.${packageNote}`, 'success');
      fetchOpsData();
    } catch (e) {
      notify(
        e.message ||
          'Error al aprobar slot (debe estar en pending_approval con pieza adjunta).',
        'error'
      );
    }
  };

  const publishFromSlot = async (slotId) => {
    try {
      const pkg = await api(`/publish/from-slot/${slotId}`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      try {
        await api(`/ops/calendar/${slotId}/advance`, {
          method: 'POST',
          body: JSON.stringify({
            actor: 'Juan Vásquez',
            target_status: 'scheduled',
            reason: 'Paquete multi-canal desde calendario.',
          }),
        });
      } catch {
        /* slot may already be scheduled */
      }
      notify(`Paquete #${pkg.id} creado desde slot #${slotId}`, 'success');
      await fetchOpsData();
      goToTab('publish');
    } catch (e) {
      notify(e.message || 'No se pudo crear paquete desde el slot', 'error');
    }
  };

  const prepareSlotApproval = async (slotId) => {
    try {
      await api(`/ops/calendar/${slotId}/prepare-approval`, {
        method: 'POST',
        body: JSON.stringify({ actor: 'Juan Vásquez' }),
      });
      await fetchOpsData();
      notify(`Slot #${slotId} listo para aprobación humana.`, 'success');
    } catch (e) {
      notify(e.message || 'Error al preparar aprobación', 'error');
    }
  };

  const completeOpsTask = async (taskId) => {
    try {
      await api(`/ops/tasks/${taskId}`, {
        method: 'PATCH',
        body: JSON.stringify({ actor: 'Juan Vásquez', status: 'in_progress' }),
      });
      await api(`/ops/tasks/${taskId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          actor: 'Juan Vásquez',
          status: 'done',
          attachment_notes: 'Completada desde panel operativo',
        }),
      });
      await fetchOpsData();
      notify('Tarea completada', 'success');
    } catch (e) {
      notify(e.message || 'Error al completar tarea', 'error');
    }
  };

  const fetchReport = async () => {
    setLoading(true);
    setReportError('');
    try {
      setReport(normalizeReport(await api('/reports/latest')));
    } catch (e) {
      console.error("Error fetching report", e);
      setReport(null);
      setReportError(e.message || 'No hay reporte aún. Genera uno con el botón Generar.');
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    setReportError('');
    await withBusy('report', async () => {
      try {
        await runBackgroundJob('/jobs/report', {
          key: 'report',
          label: 'Generando reporte semanal',
          timeoutMs: 10 * 60 * 1000,
        });
        setReport(normalizeReport(await api('/reports/latest')));
        notify('Reporte semanal generado', 'success');
      } catch (e) {
        setReportError(e.message || 'Error al generar reporte');
        notify(e.message || 'Error al generar reporte', 'error');
      }
    }, { ...JOB_META.report, background: true });
  };

  const fetchPendingBlogs = async () => {
    try {
      setPendingBlogPosts(await api('/blog/pending'));
    } catch (e) {
      console.error(e);
    }
  };

  const fetchPublishedBlogs = async () => {
    try {
      setPublishedBlogPosts(await api('/blog/published'));
    } catch (e) {
      console.error(e);
    }
  };

  const handleApproveArticle = async (articleId) => {
    await withBusy('blog', async () => {
      try {
        const job = await runBackgroundJob(`/blog/from-article/${articleId}?regenerate=true`, {
          key: 'blog',
          label: 'Preparando borrador editorial',
          timeoutMs: 10 * 60 * 1000,
        });
        const postId = job.result_json?.post_id;
        if (postId) {
          await api(`/blog/${postId}/approve`, {
            method: 'POST',
            body: JSON.stringify({ approved_by: authUser.email }),
          });
        }
        setApprovedArticleIds((prev) => new Set(prev).add(articleId));
        await fetchPendingBlogs();
        await refreshPilotSources();
        notify(`Artículo ${articleId}: borrador editorial listo para revisión.`, 'success');
      } catch (e) {
        notify(e.message || 'Error al aprobar', 'error');
      }
    }, { label: 'Preparando borrador editorial', etaSec: 120, needsOllama: true, background: true });
  };

  const handleRejectArticle = async (articleId) => {
    try {
      await api(`/articles/${articleId}/reject`, {
        method: 'POST',
        body: JSON.stringify({
          approved_by: authUser.email,
          reason: 'Rechazado durante la revisión editorial en el panel.',
        }),
      });
      setApprovedArticleIds((prev) => {
        const copy = new Set(prev);
        copy.delete(articleId);
        return copy;
      });
      await fetchArticles();
      notify(`Artículo ${articleId} rechazado y guardado.`, 'success');
    } catch (error) {
      notify(error.message || 'No se pudo rechazar el artículo', 'error');
    }
  };

  const approvePendingBlog = async (postId) => {
    try {
      await api(`/blog/${postId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: 'Juan Vasquez' }),
      });
      await fetchPendingBlogs();
      notify('Blog aprobado');
    } catch (e) {
      notify(e.message || 'Error');
    }
  };

  const publishPendingBlog = async (postId) => {
    try {
      await api(`/blog/${postId}/publish`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: 'Juan Vasquez' }),
      });
      await fetchPendingBlogs();
      await fetchPublishedBlogs();
      await refreshPilotSources();
      notify('Blog publicado', 'success');
    } catch (e) {
      notify(e.message || 'Error', 'error');
    }
  };

  const approveContentPiece = async (pieceId) => {
    if (!pieceId) return;
    try {
      await api(`/content/pieces/${pieceId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: 'Juan Vasquez' }),
      });
      notify(`Pieza ${pieceId} aprobada`, 'success');
      if (multiFormatContent?.pieces) {
        setMultiFormatContent({
          ...multiFormatContent,
          pieces: multiFormatContent.pieces.map((p) =>
            p.id === pieceId ? { ...p, status: 'approved' } : p
          ),
        });
      }
      await refreshPilotSources();
    } catch (e) {
      notify(e.message || 'Error al aprobar pieza', 'error');
    }
  };

  const reuseContentPiece = async (pieceId) => {
    if (!pieceId) return;
    try {
      const data = await api(`/content/pieces/${pieceId}/reuse`, { method: 'POST' });
      notify(`Reutilización creada: ${(data?.pieces || []).length || 0} derivados`, 'success');
    } catch (e) {
      notify(e.message || 'Error al reutilizar', 'error');
    }
  };

  const attachPieceToFirstSlot = async (pieceId, formatType = null) => {
    if (!pieceId) return;
    try {
      const piece = await api(`/content/pieces/${pieceId}`);
      const fmt = formatType || piece?.format_type;
      const slots = await api('/ops/calendar');
      const open = (slots || []).filter((s) => !s.piece_id);
      const slot =
        open.find((s) => s.format_type === fmt) ||
        open[0] ||
        (slots || []).find((s) => s.format_type === fmt) ||
        (slots || [])[0];
      if (!slot) return notify('No hay slots de calendario. Genera el calendario primero.', 'warn');
      await api(`/ops/calendar/${slot.id}/attach`, {
        method: 'POST',
        body: JSON.stringify({ actor: 'Juan Vasquez', piece_id: pieceId }),
      });
      await refreshPilotSources();
      setActiveTab('ops');
      notify(`Pieza ${pieceId} (${fmt}) adjunta al slot #${slot.id}`, 'success');
    } catch (e) {
      notify(e.message || 'Error al adjuntar', 'error');
    }
  };

  // === FASE 6: MULTIEMPRESA ===
  const fetchOrgData = async () => {
    try {
      const [ctx, orgsData, members, clients, roles] = await Promise.all([
        api('/orgs/me'),
        api('/orgs'),
        api('/orgs/members'),
        api('/orgs/clients'),
        api('/orgs/roles'),
      ]);
      setOrgContext(ctx);
      setOrgs(orgsData || []);
      setOrgMembers(members || []);
      setOrgClients(clients || []);
      setOrgRoles(roles?.roles || roles || []);
    } catch (e) {
      console.error("Error fetching org data", e);
    }
  };

  const addMember = async () => {
    if (!newMember.email || !newMember.full_name) return notify("Email y nombre son requeridos");
    try {
      await api('/orgs/members', {
        method: 'POST',
        body: JSON.stringify(newMember),
      });
      notify("Miembro agregado exitosamente");
      setNewMember({ email: '', full_name: '', role: 'writer' });
      fetchOrgData();
    } catch (e) {
      notify(e.message || "Error al agregar miembro");
    }
  };

  const onboardClient = async () => {
    if (!newClient.slug || !newClient.full_name || !newClient.email) return notify("Slug, nombre y email son requeridos");
    try {
      await api('/orgs/clients/onboard', {
        method: 'POST',
        body: JSON.stringify(newClient),
      });
      notify("Cliente onboarded exitosamente");
      setNewClient({ slug: '', full_name: '', title: '', email: '', bio: '' });
      fetchOrgData();
    } catch (e) {
      notify(e.message || "Error en onboarding");
    }
  };

  // === FASE 7: MÉTRICAS, LEADS & APRENDIZAJE ===
  const fetchMetricsData = async () => {
    try {
      const [dash, leadsData, recs] = await Promise.all([
        api('/metrics/dashboard'),
        api('/leads?limit=50'),
        api('/recommendations/percentages?status=pending'),
      ]);
      setDashboard(normalizeDashboard(dash));
      setLeads(leadsData || []);
      setRecommendations(recs || []);
    } catch (e) {
      console.error("Error fetching metrics", e);
      notify(e.message || 'Error al cargar métricas');
    }
  };

  const createLead = async () => {
    if (!newLead.contact_name) return notify("Nombre del contacto requerido", 'warn');
    try {
      const payload = {
        contact_name: newLead.contact_name,
        contact_email: newLead.contact_email || null,
        contact_company: newLead.contact_company || null,
        source_channel: newLead.source_channel || 'linkedin',
        notes: newLead.notes || null,
        pillar_id: newLead.pillar_id ? Number(newLead.pillar_id) : null,
        piece_id: newLead.piece_id ? Number(newLead.piece_id) : null,
        service_offer_id: newLead.service_offer_id ? Number(newLead.service_offer_id) : null,
        utm_source: newLead.utm_source || null,
        utm_medium: newLead.utm_medium || null,
        utm_campaign: newLead.utm_campaign || null,
        landing_url: newLead.landing_url || null,
        status: newLead.status || 'qualified',
        is_qualified: true,
      };
      await api('/leads', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      notify("Lead registrado exitosamente", 'success');
      setNewLead({
        contact_name: '',
        contact_email: '',
        contact_company: '',
        source_channel: 'linkedin',
        notes: '',
        pillar_id: '',
        piece_id: '',
        utm_source: '',
        utm_medium: '',
        utm_campaign: '',
        service_offer_id: '',
        landing_url: '',
      });
      await fetchMetricsData();
      await refreshPilotSources();
    } catch (e) {
      notify(e.message || "Error al crear lead", 'error');
    }
  };

  const updateLeadStatus = async (leadId, status) => {
    try {
      await api(`/leads/${leadId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status, is_qualified: status === 'qualified' || status === 'converted' }),
      });
      await fetchMetricsData();
      await refreshPilotSources();
      notify(`Lead actualizado: ${status}`, 'success');
    } catch (e) {
      notify(e.message || "Error al actualizar lead", 'error');
    }
  };

  const generateRecommendation = async () => {
    setLoading(true);
    try {
      const data = await api('/recommendations/percentages/generate', { method: 'POST' });
      if (data.recommendation) {
        notify("Recomendación generada. Revisa abajo.");
      } else {
        notify(data.message || "Datos insuficientes para generar recomendación.");
      }
      fetchMetricsData();
    } catch (e) {
      notify("Error al generar recomendación");
    } finally {
      setLoading(false);
    }
  };

  const decideRecommendation = async (recId, accept) => {
    try {
      await api(`/recommendations/percentages/${recId}/decide`, {
        method: 'POST',
        body: JSON.stringify({
          actor: 'Juan Vásquez',
          accept,
          reason: accept ? 'Aprobado desde dashboard' : 'Rechazado desde dashboard',
        }),
      });
      notify(accept ? "Recomendación ACEPTADA — porcentajes actualizados" : "Recomendación RECHAZADA");
      fetchMetricsData();
      fetchProfile();
    } catch (e) {
      notify("Error al decidir recomendación");
    }
  };

  const parseSummaryJson = (summaryStr) => {
    if (!summaryStr) return null;
    try {
      return JSON.parse(summaryStr);
    } catch {
      return null;
    }
  };

  const parseCarouselJson = (slides) => {
    // normalizePackage ya entrega un array [{slide, title, content}]
    if (Array.isArray(slides)) return slides;
    if (!slides) return [];
    if (typeof slides === 'object' && Array.isArray(slides.slides)) {
      return normalizeCarouselSlides({ body_json: slides });
    }
    if (typeof slides === 'string') {
      try {
        const parsed = JSON.parse(slides);
        return normalizeCarouselSlides({ body_json: parsed, body_text: slides });
      } catch {
        return slides.trim()
          ? [{ slide: 1, title: 'Carrusel', content: slides.slice(0, 500) }]
          : [];
      }
    }
    return [];
  };

  if (!authUser) {
    return (
      <LoginScreen
        onSuccess={(data) => {
          setAuthUser({
            email: data.email,
            user_id: data.user_id,
            roles_by_org: data.roles_by_org || {},
          });
        }}
      />
    );
  }

  // Solo al generar tras “Usar esta noticia”; oculto en el resto de jobs/pantallas.
  const activityPanel =
    formatGenBanner && robotJob?.key === 'multiformat' ? (
      <ActivityCenter
        status={ollamaStatus}
        job={robotJob}
        onRefresh={async () => {
          const status = await checkOllamaStatus();
          if (status?.connected) notify(`Motor editorial online · ${status.model}`, 'success');
          else notify(status?.error || 'Motor editorial sin conexión', 'error');
        }}
      />
    ) : null;

  const workflowPanel = null;

  return (
    <>
      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type || 'info'}`}>
            {t.message}
          </div>
        ))}
      </div>
      <AppShell
        activeTab={activeTab}
        onNavigate={goToTab}
        userEmail={authUser.email}
        healthInfo={healthInfo}
        onCollect={triggerIngest}
        collecting={loading || isBusy('collect')}
        onLogout={async () => {
          await logout();
          setAuthUser(null);
          setHealthInfo(null);
        }}
        activity={activityPanel}
        workflow={workflowPanel}
      >
        {activeTab === 'hoy' && (
          <HoyTab
            steps={PILOT_STEPS}
            progress={pilotProgress}
            doneCount={pilotDoneCount}
            nextStep={nextPilotStep}
            onGo={goToTab}
          />
        )}

        {activeTab === 'top10' && (
          <Top10Tab
            top10={top10}
            loading={loading}
            isSearching={isSearching}
            onRecalculate={fetchTop10}
            onPatrol={runAgenticSearch}
            onNotify={notify}
            onDerive={useArticleInFlow}
            goToTab={goToTab}
          />
        )}

        {/* TAB 9: AI GATEWAY & MÉTRICAS (FASE 5) */}
        {activeTab === 'aigateway' && (
          <AIGatewayTab
            loading={loading}
            isBusy={isBusy}
            aiUsageStats={aiUsageStats}
            aiProviders={aiProviders}
            newProvider={newProvider}
            setNewProvider={setNewProvider}
            testPrompt={testPrompt}
            setTestPrompt={setTestPrompt}
            testResult={testResult}
            onRefresh={fetchAiStats}
            onCreateProvider={createAiProvider}
            onRunTest={runGatewayTest}
          />
        )}

        {activeTab === 'agents' && (
          <AgentsTab
            isBusy={isBusy}
            agentsCatalog={agentsCatalog}
            agentArticleId={agentArticleId}
            setAgentArticleId={setAgentArticleId}
            agentLimit={agentLimit}
            setAgentLimit={setAgentLimit}
            agentPipelineMode={agentPipelineMode}
            setAgentPipelineMode={setAgentPipelineMode}
            agentReason={agentReason}
            setAgentReason={setAgentReason}
            agentRunResult={agentRunResult}
            onRefresh={fetchAgentsCatalog}
            onRunPipeline={runAgentsPipeline}
            onRunNamed={runNamedAgent}
          />
        )}

        {/* TAB 8: CALENDARIO, TAREAS & SEMÁFORO DE RIESGO (FASE 4) */}
        {activeTab === 'ops' && (
          <OpsCalendarTab
            loading={loading}
            calendarSlots={calendarSlots}
            decisionLogs={decisionLogs}
            onGenerateCalendar={async () => {
              try {
                await api('/ops/cadence/seed', { method: 'POST' });
                await api('/ops/calendar/generate', { method: 'POST', body: JSON.stringify({ weeks: 2 }) });
                await fetchOpsData();
                notify('Calendario generado (2 semanas)');
              } catch (e) {
                notify(e.message || 'Error al generar calendario');
              }
            }}
            onRefresh={fetchOpsData}
            onCompleteTask={completeOpsTask}
            onApproveSlot={approveSlot}
            onPublishFromSlot={publishFromSlot}
            onPrepareApproval={prepareSlotApproval}
          />
        )}

        {activeTab === 'refresh' && <RefreshTab notify={notify} />}

        {activeTab === 'multiformat' && (
          <MultiFormatTab
            selectedArticleForApproval={selectedArticleForApproval}
            selectedLanguage={selectedLanguage}
            onLanguageChange={changeFormatLanguage}
            fetchMultiFormat={fetchMultiFormat}
            formatBusy={isBusy('multiformat')}
            selectedFormatSubTab={selectedFormatSubTab}
            setSelectedFormatSubTab={setSelectedFormatSubTab}
            multiFormatError={multiFormatError}
            multiFormatContent={multiFormatContent}
            loading={loading}
            isBusy={isBusy}
            notify={notify}
            approveContentPiece={approveContentPiece}
            reuseContentPiece={reuseContentPiece}
            attachPieceToFirstSlot={attachPieceToFirstSlot}
            parseCarouselJson={parseCarouselJson}
            goToTab={goToTab}
          />
        )}

        {activeTab === 'profile' && (
          <ProfileTab
            profile={profile}
            pillarDrafts={pillarDrafts}
            setPillarDrafts={setPillarDrafts}
            saveProfilePercentages={saveProfilePercentages}
          />
        )}

        {activeTab === 'approval' && (
          <ApprovalTab
            selectedArticleForApproval={selectedArticleForApproval}
            goToTab={goToTab}
            handleApproveArticle={handleApproveArticle}
            handleRejectArticle={handleRejectArticle}
            pendingBlogPosts={pendingBlogPosts}
            approvePendingBlog={approvePendingBlog}
            publishPendingBlog={publishPendingBlog}
            parseSummaryJson={parseSummaryJson}
            triggerAnalyzeArticle={triggerAnalyzeArticle}
            loading={loading}
          />
        )}

        {activeTab === 'blog' && (
          <BlogTab
            publishedBlogPosts={publishedBlogPosts}
            pendingBlogPosts={pendingBlogPosts}
            approvePendingBlog={approvePendingBlog}
            publishPendingBlog={publishPendingBlog}
          />
        )}

        {activeTab === 'publish' && (
          <PublishTab notify={notify} publishedBlogPosts={publishedBlogPosts} goToTab={goToTab} />
        )}

        {activeTab === 'legalseo' && <LegalSeoTab notify={notify} />}

        {activeTab === 'marketing' && <MarketingTab notify={notify} />}

        {activeTab === 'report' && (
          <ReportTab
            loading={loading}
            generateReport={generateReport}
            report={report}
            reportError={reportError}
            notify={notify}
          />
        )}

        {/* TAB 5: EXPLORADOR DE NOTICIAS & INGESTA */}
        {activeTab === 'live' && (
          <LiveNewsTab
            categories={categories}
            selectedCategory={selectedCategory}
            setSelectedCategory={setSelectedCategory}
            searchQuery={searchQuery}
            onSearchInput={onSearchInput}
            articles={articles}
            articlesTotalHint={articlesTotalHint}
            isBusy={isBusy}
            onFetchArticles={fetchArticles}
            onUseInFlow={useArticleInFlow}
            onClearFilters={() => {
              setSearchQuery('');
              setSelectedCategory('');
              fetchArticles('', '');
            }}
          />
        )}

        {activeTab === 'multiempresa' && (
          <MultiEmpresaTab
            orgContext={orgContext}
            orgs={orgs}
            orgMembers={orgMembers}
            orgClients={orgClients}
            orgRoles={orgRoles}
            newMember={newMember}
            setNewMember={setNewMember}
            addMember={addMember}
            newClient={newClient}
            setNewClient={setNewClient}
            onboardClient={onboardClient}
            notify={notify}
            onOrgRefresh={fetchOrgData}
          />
        )}

        {activeTab === 'metrics' && (
          <MetricsTab
            dashboard={dashboard}
            leads={leads}
            leadFilter={leadFilter}
            setLeadFilter={setLeadFilter}
            updateLeadStatus={updateLeadStatus}
            newLead={newLead}
            setNewLead={setNewLead}
            createLead={createLead}
            recommendations={recommendations}
            generateRecommendation={generateRecommendation}
            decideRecommendation={decideRecommendation}
            loading={loading}
            profile={profile}
            goToTab={goToTab}
          />
        )}

      </AppShell>
    </>
  );
}
