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
import AIHubTab from './tabs/AIHubTab';
import LiveNewsTab from './tabs/LiveNewsTab';
import MultiFormatTab from './tabs/MultiFormatTab';
import ProfileTab from './tabs/ProfileTab';
import ReportTab from './tabs/ReportTab';
import MultiEmpresaTab from './tabs/MultiEmpresaTab';
import MetricsTab from './tabs/MetricsTab';
import HoyTab from './tabs/HoyTab';
import { enqueueJob, getRememberedJobs, waitForJob } from './jobs';
import { normalizeTop10, normalizeArticle } from './utils/normalizers';

export default function App() {
  const [authUser, setAuthUser] = useState(() => (isAuthenticated() ? getStoredUser() : null));
  const [healthInfo, setHealthInfo] = useState(null);
  const [activeTab, setActiveTab] = useState('hoy');

  useEffect(() => {
    // Pestañas ocultas: si el estado quedó ahí, vuelve a Hoy
    if (['refresh', 'legalseo', 'agents', 'approval', 'metrics', 'top10', 'report', 'multiempresa'].includes(activeTab)) {
      setActiveTab(activeTab === 'agents' ? 'aigateway' : 'hoy');
    }
  }, [activeTab]);
  const [articles, setArticles] = useState([]);
  const [top10, setTop10] = useState([]);
  const [top10Error, setTop10Error] = useState('');
  const [articlesError, setArticlesError] = useState('');
  const [profileError, setProfileError] = useState('');
  const [categories, setCategories] = useState([]);
  const [profile, setProfile] = useState(null);
  const [report, setReport] = useState(null);
  const [multiFormatContent, setMultiFormatContent] = useState(null);
  const [aiProviders, setAiProviders] = useState([]);
  const [aiUsageStats, setAiUsageStats] = useState(null);
  const [aiStatsError, setAiStatsError] = useState('');
  const [testPrompt, setTestPrompt] = useState('Analiza las implicaciones legales y de gobernanza de la IA generativa.');
  const [testResult, setTestResult] = useState(null);
  const [selectedFormatSubTab, setSelectedFormatSubTab] = useState('linkedin');
  const [selectedLanguage, setSelectedLanguage] = useState('es');
  const [providerMode, setProviderMode] = useState('local'); // local | cloud | auto
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
  const [workedArticleIds, setWorkedArticleIds] = useState(() => {
    try {
      const raw = localStorage.getItem('a360_worked_articles');
      const ids = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(ids) ? ids.map(Number).filter(Number.isFinite) : []);
    } catch {
      return new Set();
    }
  });

  const markArticleWorked = (articleId) => {
    const id = Number(articleId);
    if (!Number.isFinite(id)) return;
    setWorkedArticleIds((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      try {
        localStorage.setItem('a360_worked_articles', JSON.stringify([...next]));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

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
    name: 'OpenAI',
    provider_type: 'openai',
    model_name: 'gpt-4o',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    monthly_budget_usd: '',
    priority: 20,
  });
  const [pendingBlogPosts, setPendingBlogPosts] = useState([]);
  const [publishedBlogPosts, setPublishedBlogPosts] = useState([]);
  const [editorialBlogPosts, setEditorialBlogPosts] = useState([]);
  const [pillarDrafts, setPillarDrafts] = useState({});
  const [themeDrafts, setThemeDrafts] = useState([]);
  const [pctRecommendation, setPctRecommendation] = useState(null);
  const [pctRecMessage, setPctRecMessage] = useState(null);
  const [pctRecLoading, setPctRecLoading] = useState(false);
  const [adTrendNotes, setAdTrendNotes] = useState(null);
  const [adTrendMessage, setAdTrendMessage] = useState(null);
  const [adTrendBusy, setAdTrendBusy] = useState(false);
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
    fetchAdTrendNotes();
    refreshPilotSources();
    ensureAiProviders({ force: true });
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
      const [blogs, pending, leadsData, packages] = await Promise.all([
        api('/blog/published').catch(() => []),
        api('/blog/pending').catch(() => []),
        api('/leads?limit=50').catch(() => []),
        api('/content/packages?limit=20').catch(() => []),
      ]);
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
    if (tab === 'approval') tab = 'multiformat';
    if (tab === 'publish' || tab === 'blog') tab = 'multiformat';
    if (tab === 'marketing') tab = 'hoy';
    if (tab === 'legalseo') tab = 'hoy';
    if (tab === 'agents') tab = 'aigateway';
    if (tab === 'refresh') tab = 'hoy';
    if (tab === 'top10') tab = 'hoy';
    if (tab === 'report') tab = 'hoy';
    if (tab === 'multiempresa') tab = 'hoy';
    setActiveTab(tab);
    if (tab === 'aigateway') {
      fetchAiStats();
      fetchAgentsCatalog();
    }
    if (tab === 'profile') {
      fetchProfile();
      fetchPctRecommendation(false);
    }
    if (tab === 'hoy') {
      fetchProfile();
      fetchTop10();
      fetchAdTrendNotes();
    }
    if (tab === 'report') fetchReport();
    if (tab === 'multiempresa') fetchOrgData();
    if (tab === 'metrics') fetchMetricsData();
    if (tab === 'multiformat') {
      fetchPendingBlogs();
      fetchPublishedBlogs();
      fetchEditorialBlogs(selectedArticleForApproval?.id || null);
    }
    if (tab === 'live') fetchArticles();
    if (['metrics', 'multiformat'].includes(tab)) {
      refreshPilotSources();
    }
  };

  const useArticleInFlow = (art) => {
    const normalized = normalizeArticle(art);
    const articleId = art.article_id ?? art.id;
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
    markArticleWorked(articleId);
    setMultiFormatContent(null);
    setMultiFormatError('');
    setSelectedArticleForApproval({
      ...normalized,
      id: articleId,
      content_full: art.summary || art.content_full || '',
      summary: art.summary || '',
      url: art.source_url || art.url,
    });
    setActiveTab('multiformat');
    fetchPendingBlogs();
    fetchPublishedBlogs();
    fetchEditorialBlogs(articleId);
    // La generación solo arranca cuando el usuario autoriza en Generar formatos
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

  const workedArticleIdSet = useMemo(() => {
    const ids = new Set(workedArticleIds);
    for (const pkg of contentPackages || []) {
      const id = Number(pkg.article_id ?? pkg.article?.id);
      if (Number.isFinite(id)) ids.add(id);
    }
    for (const piece of allPieces) {
      const id = Number(piece.article_id);
      if (Number.isFinite(id)) ids.add(id);
    }
    const currentId = Number(multiFormatContent?.article_id ?? selectedArticleForApproval?.id);
    if (Number.isFinite(currentId)) ids.add(currentId);
    return ids;
  }, [
    workedArticleIds,
    contentPackages,
    allPieces,
    multiFormatContent,
    selectedArticleForApproval,
  ]);

  const pilotProgress = useMemo(() => {
    const hasFormats = allPieces.length > 0 || (contentPackages || []).length > 0;
    const hasChosen =
      Boolean(selectedArticleForApproval) || hasFormats;
    const hasApprovedPiece =
      allPieces.some((p) => p.status === 'approved') ||
      approvedArticleIds.size > 0 ||
      (pendingBlogPosts || []).some((p) => p.status === 'approved');
    const hasPublished = (publishedBlogPosts || []).length > 0;
    return {
      elegir: hasChosen,
      approval: hasApprovedPiece,
      publish: hasPublished,
    };
  }, [
    selectedArticleForApproval,
    allPieces,
    contentPackages,
    approvedArticleIds,
    pendingBlogPosts,
    publishedBlogPosts,
    pilotTick,
  ]);

  const PILOT_STEPS = [
    {
      id: 'elegir',
      label: 'Elegir y generar',
      tab: 'hoy',
      hint: 'Usa una noticia del ranking de arriba',
      cta: 'Ver ranking',
    },
    {
      id: 'publish',
      label: 'Estudio / publicar',
      tab: 'multiformat',
      hint: 'Preview, chat IA, redes y blog en el Estudio',
      cta: 'Abrir estudio',
    },
  ];
  const pilotDoneCount = PILOT_STEPS.filter((s) => pilotProgress[s.id]).length;
  const nextPilotStep = PILOT_STEPS.find((s) => !pilotProgress[s.id]) || null;

  const fetchCategories = async () => {
    try {
      const data = await api('/articles?limit=100&max_age_hours=36');
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
      setProfileError('');
      const drafts = {};
      for (const p of data?.pillars || []) drafts[p.slug] = p.target_percentage;
      setPillarDrafts(drafts);
      setThemeDrafts(
        (data?.search_themes || []).map((t) => ({
          ...t,
          queries: Array.isArray(t.queries) ? t.queries : [],
          is_active: t.is_active !== false,
        }))
      );
    } catch (e) {
      console.error("Error fetching profile", e);
      setProfileError(e.message || 'No se pudo cargar el perfil.');
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

  const saveSearchThemes = async () => {
    if (!profile) return;
    const cleaned = (themeDrafts || [])
      .map((t) => ({
        ...t,
        name: (t.name || '').trim(),
        queries: Array.isArray(t.queries) ? t.queries.filter(Boolean) : [],
      }))
      .filter((t) => t.name);
    if (!cleaned.length) {
      notify('Agrega al menos un tema con nombre.');
      return;
    }
    try {
      const data = normalizeProfile(
        await api('/profile/search-themes', {
          method: 'PUT',
          body: JSON.stringify({ themes: cleaned }),
        })
      );
      setProfile(data);
      setThemeDrafts(
        (data?.search_themes || []).map((t) => ({
          ...t,
          queries: Array.isArray(t.queries) ? t.queries : [],
          is_active: t.is_active !== false,
        }))
      );
      notify('Temas de búsqueda guardados. La patrulla usará estas queries.');
    } catch (e) {
      notify(e.message || 'Error al guardar temas de búsqueda');
    }
  };

  const resetSearchThemes = async () => {
    if (!window.confirm('¿Restaurar las 11 tipologías del PDF de Juan Vásquez? Se perderán temas custom.')) {
      return;
    }
    try {
      const data = normalizeProfile(
        await api('/profile/search-themes', {
          method: 'PUT',
          body: JSON.stringify({ themes: [], reset_to_defaults: true }),
        })
      );
      setProfile(data);
      setThemeDrafts(
        (data?.search_themes || []).map((t) => ({
          ...t,
          queries: Array.isArray(t.queries) ? t.queries : [],
          is_active: t.is_active !== false,
        }))
      );
      notify('Tipologías del PDF restauradas.');
    } catch (e) {
      notify(e.message || 'Error al restaurar tipologías');
    }
  };

  const applyPdfPillarMix = async () => {
    if (!window.confirm('¿Aplicar el mix editorial del PDF (30/25/20/15/10)? Se actualizarán nombres y metas de pilares.')) {
      return;
    }
    try {
      const data = normalizeProfile(
        await api('/profile/pillars/rebalance', { method: 'POST' })
      );
      setProfile(data);
      const drafts = {};
      for (const p of data?.pillars || []) drafts[p.slug] = p.target_percentage;
      setPillarDrafts(drafts);
      notify('Mix editorial PDF aplicado (Legal Tech–IA 30%, Compliance 25%, PI 20%, MX–US 15%, Inversión 10%).');
    } catch (e) {
      notify(e.message || 'Error al aplicar mix PDF');
    }
  };

  const fetchPctRecommendation = async (generate = false) => {
    setPctRecLoading(true);
    try {
      const qs = generate ? '?generate=true&days=1' : '?generate=false&days=1';
      const data = await api(`/profile/percentage-recommendations${qs}`);
      setPctRecommendation(data?.recommendation || null);
      setPctRecMessage(data?.message || null);
    } catch (e) {
      setPctRecommendation(null);
      setPctRecMessage(e.message || 'No se pudo cargar la sugerencia de mix');
    } finally {
      setPctRecLoading(false);
    }
  };

  const acceptPctRecommendation = async (recId) => {
    if (!recId) return;
    setPctRecLoading(true);
    try {
      const data = normalizeProfile(
        await api(`/profile/percentage-recommendations/${recId}/accept`, { method: 'POST' })
      );
      setProfile(data);
      const drafts = {};
      for (const p of data?.pillars || []) drafts[p.slug] = p.target_percentage;
      setPillarDrafts(drafts);
      setPctRecommendation(null);
      setPctRecMessage(null);
      notify('Mix editorial actualizado. El boost de Hoy usará las nuevas metas.');
      fetchTop10();
    } catch (e) {
      notify(e.message || 'No se pudo aprobar la sugerencia', 'error');
    } finally {
      setPctRecLoading(false);
    }
  };

  const rejectPctRecommendation = async (recId) => {
    if (!recId) return;
    setPctRecLoading(true);
    try {
      await api(`/profile/percentage-recommendations/${recId}/reject`, { method: 'POST' });
      setPctRecommendation(null);
      setPctRecMessage('Sugerencia rechazada. Las metas no cambiaron.');
      notify('Sugerencia de mix rechazada');
    } catch (e) {
      notify(e.message || 'No se pudo rechazar la sugerencia', 'error');
    } finally {
      setPctRecLoading(false);
    }
  };

  const fetchAdTrendNotes = async () => {
    try {
      const data = await api('/profile/ad-trend-notes');
      setAdTrendNotes(data?.notes || null);
      setAdTrendMessage(data?.message || null);
    } catch (e) {
      setAdTrendNotes(null);
      setAdTrendMessage(e.message || 'No se pudieron cargar las notas');
    }
  };

  const generateAdTrendNotes = async () => {
    setAdTrendBusy(true);
    try {
      const data = await api('/profile/ad-trend-notes/generate', { method: 'POST' });
      setAdTrendNotes(data?.notes || null);
      setAdTrendMessage(null);
      notify('Notas de tendencias y publicidad actualizadas');
    } catch (e) {
      notify(e.message || 'No se pudieron generar las notas', 'error');
    } finally {
      setAdTrendBusy(false);
    }
  };

  const generateAdNoteImage = async (platform) => {
    const data = await api(
      `/profile/ad-trend-notes/generate-image?platform=${encodeURIComponent(platform)}&use_openai=true`,
      { method: 'POST' }
    );
    if (data?.notes) setAdTrendNotes(data.notes);
    return data?.note || null;
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
      setAiStatsError('');
      return pData || [];
    } catch (e) {
      console.error("Error fetching AI stats", e);
      setAiStatsError(e.message || 'No se pudieron cargar los proveedores de IA.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  /** Carga silenciosa de proveedores (sin bloquear UI con loading global). */
  const ensureAiProviders = async ({ force = false } = {}) => {
    if (!force && Array.isArray(aiProviders) && aiProviders.length > 0) {
      return aiProviders;
    }
    try {
      const pData = await api('/ai/providers');
      const list = pData || [];
      setAiProviders(list);
      return list;
    } catch (e) {
      console.error('Error loading AI providers', e);
      return aiProviders || [];
    }
  };

  const hasCloudApiProvider = (providers) =>
    (providers || []).some(
      (p) =>
        p.is_active &&
        !p.is_local &&
        (p.has_api_key || Boolean(p.key_hint))
    );

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
          max_results_per_query: 5,
          max_queries: 14,
          max_priority: 11,
          max_age_hours: 36,
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
        const stale = res.stats?.rejected_stale ?? 0;
        notify(
          `Patrulla del día: ${res.stats?.saved_to_db || 0} nuevas · viejas descartadas ${stale} · baja relevancia ${res.stats?.rejected_low_relevance || 0} · ${res.stats?.urls_found || 0} URLs${typeSummary ? ` · ${typeSummary}` : ''}`,
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
    const type = newProvider.provider_type || 'openai';
    const name = (newProvider.name || '').trim();
    const model = (newProvider.model_name || '').trim();
    if (!name || !model) {
      return notify('Elige un proveedor (se rellenan nombre y modelo solos)');
    }
    if (type !== 'ollama' && !(newProvider.api_key || '').trim()) {
      return notify('Pega la API key del proveedor cloud');
    }
    try {
      const body = {
        name,
        provider_type: type,
        model_name: model,
        api_key: type === 'ollama' ? null : newProvider.api_key || null,
        base_url: newProvider.base_url || null,
        monthly_budget_usd: newProvider.monthly_budget_usd
          ? Number(newProvider.monthly_budget_usd)
          : null,
        priority: Number(newProvider.priority) || 50,
      };
      await api('/ai/providers', { method: 'POST', body: JSON.stringify(body) });
      notify('Proveedor agregado. La API key queda cifrada.');
      setNewProvider({
        name: 'OpenAI',
        provider_type: 'openai',
        model_name: 'gpt-4o',
        api_key: '',
        base_url: 'https://api.openai.com/v1',
        monthly_budget_usd: '',
        priority: 20,
      });
      fetchAiStats();
    } catch (e) {
      notify(e.message || 'Error al crear proveedor');
    }
  };

  const updateAiProvider = async (providerId, patch) => {
    if (!providerId || !patch) return;
    try {
      await api(`/ai/providers/${providerId}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      });
      if (patch.api_key) {
        notify('API key re-cifrada y guardada', 'success');
      } else {
        notify(`Modelo actualizado a ${patch.model_name || 'nuevo valor'}`);
      }
      await fetchAiStats();
    } catch (e) {
      notify(e.message || 'No se pudo actualizar el proveedor', 'error');
      throw e;
    }
  };

  const removeAiProvider = async (provider) => {
    if (!provider?.id) return;
    const isDefaultLocal = provider.is_local && provider.provider_type === 'ollama';
    const action = isDefaultLocal ? 'desactivar' : 'eliminar';
    if (!window.confirm(`¿Quieres ${action} ${provider.name}?${isDefaultLocal ? ' Podrás activarlo de nuevo desde esta pantalla.' : ' Esta acción no se puede deshacer.'}`)) {
      return;
    }
    try {
      if (isDefaultLocal) {
        await api(`/ai/providers/${provider.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_active: false }),
        });
      } else {
        await api(`/ai/providers/${provider.id}`, { method: 'DELETE' });
      }
      notify(isDefaultLocal ? 'Ollama local desactivado' : `${provider.name} eliminado`, 'success');
      await fetchAiStats();
    } catch (e) {
      notify(e.message || `No se pudo ${action} el proveedor`, 'error');
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

  const fetchTop10 = async ({ persist = false } = {}) => {
    setLoading(true);
    try {
      const qs = persist
        ? '/top10?days=1&limit=10&persist=true'
        : '/top10?days=1&limit=10';
      const data = normalizeTop10(await api(qs));
      setTop10(Array.isArray(data) ? data : []);
      setTop10Error('');
      // Solo seleccionar #1; NO auto-generar LinkedIn (eso repetía siempre el mismo post)
      if (data.length > 0 && !selectedArticleForApproval) {
        setSelectedArticleForApproval(data[0]);
      }
    } catch (e) {
      console.error("Error fetching Top 10", e);
      notify(e.message || 'No se pudo cargar el Top 10', 'error');
      setTop10Error(e.message || 'No se pudo cargar el ranking.');
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
      params.set('max_age_hours', '36');
      if (cat) params.set('category', cat);
      if (search && search.trim()) params.set('q', search.trim());
      const rows = (await api(`/articles?${params.toString()}`)).map(normalizeArticle);
      // Cinturón de seguridad: nunca mostrar piezas sin fecha o con fecha vieja
      const cutoff = Date.now() - 36 * 60 * 60 * 1000;
      const fresh = rows.filter((a) => {
        if (!a.published_at) return false;
        const t = new Date(a.published_at).getTime();
        return Number.isFinite(t) && t >= cutoff;
      });
      setArticles(fresh);
      setArticlesTotalHint(fresh.length);
      setArticlesError('');
      if (search && search.trim() && fresh.length === 0) {
        notify(`Sin resultados frescos para “${search.trim()}”. Prueba otra palabra o limpia el filtro.`, 'warn');
      }
    } catch (e) {
      console.error("Error fetching articles", e);
      notify(e.message || 'Error al buscar noticias', 'error');
      setArticlesError(e.message || 'No se pudo cargar el inventario de noticias.');
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
    const {
      clearContent = false,
      showBanner = false,
      formats = null,
      regenerate = false,
      packageId: packageIdOpt = null,
      providerMode: providerModeOpt = null,
    } = options;
    const mode = providerModeOpt || providerMode || 'local';
    const fmtList = Array.isArray(formats) && formats.length
      ? formats
      : [
          {
            linkedin: 'linkedin',
            video: 'video_script',
            carousel: 'carousel',
            newsletter: 'newsletter',
          }[selectedFormatSubTab] || 'linkedin',
        ];
    const fmtLabel = fmtList
      ? fmtList.map((f) => ({
          linkedin: 'LinkedIn',
          video_script: 'video',
          carousel: 'carrusel',
          newsletter: 'newsletter',
        }[f] || f)).join(', ')
      : 'formatos';
    const langLabel = lang === 'en' ? 'inglés' : 'español';
    const modeLabel = mode === 'cloud' ? 'API' : mode === 'auto' ? 'auto' : 'local';
    if (mode === 'cloud') {
      // No confiar solo en estado en memoria: tras login o sin visitar IA,
      // aiProviders puede estar vacío aunque la key ya exista en DB.
      const providers = await ensureAiProviders({
        force: !hasCloudApiProvider(aiProviders),
      });
      if (!hasCloudApiProvider(providers)) {
        notify(
          'No hay API cloud configurada. Ve a Inteligencia Artificial y agrega tu API key (OpenAI, Anthropic o Gemini).',
          'warn'
        );
        return;
      }
    }
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
              label: `Generando ${fmtLabel} (${langLabel}, ${modeLabel})`,
              body: {
                languages: [lang],
                prefer_llm: true,
                formats: fmtList,
                package_id: packageIdOpt || multiFormatContent?.id || null,
                regenerate: Boolean(regenerate),
                provider_mode: mode,
              },
              timeoutMs: 12 * 60 * 1000,
            });
            const packageId = job.result_json?.package_id;
            if (!packageId) throw new Error('El job terminó sin identificar el paquete');
            const data = normalizePackage(
              await api(`/content/packages/${packageId}`),
              lang
            );
            setMultiFormatContent(data);
            setSelectedLanguage(lang);
            markArticleWorked(articleId);
            const modes = (data.pieces || [])
              .filter((p) => !fmtList || fmtList.includes(p.format_type))
              .map((p) => p.generation_mode)
              .filter(Boolean);
            const det = modes.filter((m) => m === 'deterministic').length;
            if (det > 0) {
              notify(
                `${fmtLabel} listo en ${langLabel}, pero usó plantilla. Reintenta si el idioma no cuadra.`,
                'warn'
              );
            } else {
              notify(`${fmtLabel} listo en ${langLabel} (${modeLabel})`, 'success');
            }
            refreshPilotSources();
          } catch (e) {
            console.error('Error fetching multi-format content', e);
            setMultiFormatError(e.message || 'Error al generar formato');
            notify(e.message || 'Error al generar formato', 'error');
          }
        },
        {
          ...JOB_META.multiformat,
          background: true,
          label: `Generando ${fmtLabel} (${langLabel}, ${modeLabel})`,
          etaSec: mode === 'cloud' ? 45 : (fmtList?.length === 1 ? 90 : JOB_META.multiformat.etaSec),
          needsOllama: mode !== 'cloud',
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
    // Solo regenera el formato de la pestaña activa
    const subToFmt = {
      linkedin: 'linkedin',
      video: 'video_script',
      carousel: 'carousel',
      newsletter: 'newsletter',
    };
    const fmt = subToFmt[selectedFormatSubTab] || 'linkedin';
    fetchMultiFormat(selectedArticleForApproval.id, lang, {
      clearContent: false,
      showBanner: true,
      formats: [fmt],
      regenerate: true,
      packageId: multiFormatContent?.id || null,
    });
  };

  const collectJobRef = useRef(null);

  const triggerIngest = async () => {
    if (collectJobRef.current || isBusy('collect')) {
      notify('Ya hay una recolección en curso. Espera a que termine.', 'info');
      return;
    }

    setBusy((b) => ({ ...b, collect: true }));
    let jobId = null;
    try {
      const job = await enqueueJob('/jobs/collect', {
        label: 'Actualizando fuentes de noticias',
      });
      jobId = job.id;
      collectJobRef.current = job.id;
      setRobotJob({
        key: 'collect',
        label: 'Actualizando fuentes de noticias',
        jobId: job.id,
        status: job.status,
        startedAt: Date.now(),
        etaSec: JOB_META.collect?.etaSec || 600,
        needsOllama: false,
      });
      notify(
        'Recolección iniciada. Puede tardar varios minutos; puedes seguir usando la app.',
        'success'
      );
    } catch (e) {
      notify(e.message || 'No se pudo iniciar la recolección RSS', 'error');
      return;
    } finally {
      setBusy((b) => {
        const next = { ...b };
        delete next.collect;
        return next;
      });
    }

    waitForJob(jobId, {
      timeoutMs: 20 * 60 * 1000,
      onUpdate: (update) => {
        setRobotJob((current) => ({
          ...(current || {}),
          key: 'collect',
          label: 'Actualizando fuentes de noticias',
          jobId: update.id,
          status: update.status,
          startedAt: current?.startedAt || Date.now(),
          etaSec: JOB_META.collect?.etaSec || 600,
          needsOllama: false,
        }));
      },
    })
      .then(() => {
        notify('Fuentes actualizadas correctamente.', 'success');
        fetchCategories();
        fetchTop10();
        fetchArticles();
        fetchProfile();
      })
      .catch((e) => {
        if (e.name !== 'AbortError') {
          notify(e.message || 'Error al ejecutar recolección RSS', 'error');
        }
      })
      .finally(() => {
        collectJobRef.current = null;
        setRobotJob((current) => (current?.key === 'collect' ? null : current));
      });
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

  const fetchEditorialBlogs = async (articleId = null) => {
    try {
      const qs = articleId ? `?article_id=${articleId}` : '';
      const rows = await api(`/blog/editorial${qs}`);
      setEditorialBlogPosts(Array.isArray(rows) ? rows : []);
      return rows;
    } catch (e) {
      console.error(e);
      setEditorialBlogPosts([]);
      return [];
    }
  };

  const fetchPublishedBlogs = async () => {
    try {
      setPublishedBlogPosts(await api('/blog/published'));
    } catch (e) {
      console.error(e);
    }
  };

  /** Estudio: genera borrador en sincronía (sin Celery) para que siempre aparezca en la lista. */
  const generateStudioBlogDraft = async (articleId) => {
    const id = Number(articleId);
    if (!Number.isFinite(id) || id <= 0) {
      notify('No hay noticia seleccionada para el blog', 'error');
      return;
    }
    await withBusy('blog', async () => {
      try {
        const post = await api(`/blog/from-article/${id}?regenerate=true`, {
          method: 'POST',
        });
        // Mostrar de inmediato el post devuelto (no esperar solo al listado).
        if (post?.id) {
          setEditorialBlogPosts((prev) => {
            const rest = (prev || []).filter((p) => p.id !== post.id);
            return [post, ...rest];
          });
        }
        await fetchPendingBlogs();
        await fetchEditorialBlogs(id);
        await refreshPilotSources();
        notify(
          `Artículo listo: “${(post?.title || 'Borrador').slice(0, 80)}”. Revisa el texto abajo → Publicar para exponerlo.`,
          'success'
        );
        return post;
      } catch (e) {
        notify(e.message || 'No se pudo generar el artículo de blog', 'error');
        return null;
      }
    }, { label: 'Generando artículo de blog', etaSec: 90, needsOllama: true, background: false });
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
        await fetchEditorialBlogs(articleId);
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
      setSelectedArticleForApproval(null);
      setMultiFormatContent(null);
      setMultiFormatError('');
      await fetchArticles();
      notify(`Artículo ${articleId} rechazado.`, 'success');
      setActiveTab('hoy');
    } catch (error) {
      notify(error.message || 'No se pudo rechazar el artículo', 'error');
    }
  };

  const approvePendingBlog = async (postId) => {
    try {
      await api(`/blog/${postId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: authUser?.email || 'Juan Vasquez' }),
      });
      await fetchPendingBlogs();
      await fetchEditorialBlogs(selectedArticleForApproval?.id || null);
      notify('Blog aprobado. Ya puedes publicarlo para exponerlo.', 'success');
    } catch (e) {
      notify(e.message || 'Error', 'error');
    }
  };

  const publishPendingBlog = async (postId) => {
    try {
      const published = await api(`/blog/${postId}/publish`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: authUser?.email || 'Juan Vasquez' }),
      });
      await fetchPendingBlogs();
      await fetchPublishedBlogs();
      await fetchEditorialBlogs(selectedArticleForApproval?.id || null);
      await refreshPilotSources();
      const slug = published?.slug;
      const publicUrl = slug
        ? (import.meta.env.VITE_PUBLIC_BLOG_POST_URL || 'http://127.0.0.1:3002/blog/{slug}').replace(
            '{slug}',
            encodeURIComponent(slug)
          )
        : import.meta.env.VITE_PUBLIC_BLOG_URL || 'http://127.0.0.1:3002';
      notify('Blog publicado. Abriendo sitio público…', 'success');
      window.open(publicUrl, '_blank', 'noopener,noreferrer');
      return published;
    } catch (e) {
      notify(e.message || 'Error al publicar', 'error');
      return null;
    }
  };

  const approveContentPiece = async (pieceId) => {
    if (!pieceId) {
      notify('No hay pieza para aprobar. Genera los formatos primero.', 'warn');
      return;
    }
    const existing = (multiFormatContent?.pieces || []).find((p) => p.id === pieceId);
    if (existing?.status === 'approved') {
      notify('Esa pieza ya está aprobada', 'success');
      return;
    }
    try {
      await api(`/content/pieces/${pieceId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: authUser?.email || 'Juan Vasquez' }),
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
      if (selectedArticleForApproval?.id) {
        setApprovedArticleIds((prev) => new Set(prev).add(selectedArticleForApproval.id));
      }
      await refreshPilotSources();
    } catch (e) {
      notify(e.message || 'Error al aprobar pieza', 'error');
    }
  };

  /** Aprueba los formatos generados de la noticia en curso (no lanza blog en silencio). */
  const approveGeneratedPackage = async (draftOverrides = null) => {
    // Puede recibir drafts editados; si llega un id numérico (legacy), se ignora
    if (draftOverrides != null && (typeof draftOverrides !== 'object' || Array.isArray(draftOverrides))) {
      draftOverrides = null;
    }
    const ids = [
      multiFormatContent?.linkedin_piece_id,
      multiFormatContent?.video_piece_id,
      multiFormatContent?.carousel_piece_id,
      multiFormatContent?.newsletter_piece_id,
    ].filter(Boolean);

    if (!ids.length) {
      notify('Genera los formatos antes de aprobar la noticia.', 'warn');
      return;
    }

    // Persistir ediciones locales pendientes antes de aprobar
    if (draftOverrides && typeof draftOverrides === 'object') {
      const saves = [
        ['linkedin_post', multiFormatContent.linkedin_piece_id],
        ['video_script', multiFormatContent.video_piece_id],
        ['carousel_slides', multiFormatContent.carousel_piece_id],
        ['newsletter_edition', multiFormatContent.newsletter_piece_id],
      ];
      for (const [field, pieceId] of saves) {
        if (!pieceId || draftOverrides[field] == null) continue;
        const current =
          field === 'carousel_slides'
            ? (typeof multiFormatContent.carousel_slides === 'string'
                ? multiFormatContent.carousel_slides
                : JSON.stringify(multiFormatContent.carousel_slides || [], null, 2))
            : multiFormatContent[field] || '';
        if (String(draftOverrides[field]) !== String(current)) {
          try {
            await api(`/content/pieces/${pieceId}`, {
              method: 'PATCH',
              body: JSON.stringify({ body_text: draftOverrides[field] }),
            });
          } catch (e) {
            notify(`No se pudo guardar ${field} antes de aprobar: ${e.message || 'error'}`, 'error');
            return;
          }
        }
      }
    }

    const actor = authUser?.email || 'Juan Vasquez';
    let ok = 0;
    let skipped = 0;
    const errors = [];
    const piecesById = Object.fromEntries((multiFormatContent?.pieces || []).map((p) => [p.id, p]));

    for (const id of ids) {
      if (piecesById[id]?.status === 'approved') {
        skipped += 1;
        ok += 1;
        continue;
      }
      try {
        await api(`/content/pieces/${id}/approve`, {
          method: 'POST',
          body: JSON.stringify({ approved_by: actor }),
        });
        ok += 1;
      } catch (e) {
        errors.push(`#${id}: ${e.message || 'error'}`);
      }
    }

    if (ok > 0 && selectedArticleForApproval?.id) {
      setApprovedArticleIds((prev) => new Set(prev).add(selectedArticleForApproval.id));
    }
    if (multiFormatContent?.pieces) {
      const failed = new Set(
        errors.map((msg) => {
          const m = /^#(\d+)/.exec(msg);
          return m ? Number(m[1]) : null;
        }).filter(Boolean)
      );
      setMultiFormatContent({
        ...multiFormatContent,
        pieces: multiFormatContent.pieces.map((p) =>
          ids.includes(p.id) && !failed.has(p.id) ? { ...p, status: 'approved' } : p
        ),
      });
    }
    await refreshPilotSources();
    if (ok && !errors.length) {
      notify(
        skipped === ids.length
          ? 'Los formatos de esta noticia ya estaban aprobados.'
          : `${ok} formato(s) aprobados. Ya puedes publicar.`,
        'success'
      );
    } else if (ok) {
      notify(`${ok} aprobado(s); fallaron: ${errors.join('; ')}`, 'warn');
    } else {
      notify(errors[0] || 'No se pudo aprobar ningún formato', 'error');
    }
  };

  const updateContentPiece = async (pieceId, bodyText, fieldKey) => {
    if (!pieceId) {
      notify('No hay pieza para guardar', 'warn');
      return;
    }
    try {
      await api(`/content/pieces/${pieceId}`, {
        method: 'PATCH',
        body: JSON.stringify({ body_text: bodyText }),
      });
      setMultiFormatContent((prev) => {
        if (!prev) return prev;
        const next = { ...prev };
        if (fieldKey === 'linkedin_post') next.linkedin_post = bodyText;
        if (fieldKey === 'video_script') next.video_script = bodyText;
        if (fieldKey === 'newsletter_edition') next.newsletter_edition = bodyText;
        if (fieldKey === 'carousel_slides') {
          try {
            const parsed = JSON.parse(bodyText);
            next.carousel_slides = Array.isArray(parsed) ? parsed : parsed?.slides || bodyText;
          } catch {
            next.carousel_slides = bodyText;
          }
        }
        next.pieces = (prev.pieces || []).map((p) =>
          p.id === pieceId ? { ...p, body_text: bodyText, status: p.status === 'approved' ? 'pending_approval' : p.status } : p
        );
        return next;
      });
      notify('Contenido guardado', 'success');
    } catch (e) {
      notify(e.message || 'No se pudo guardar el contenido', 'error');
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

  // Progreso visible: generar formatos (banner) o recolección RSS en curso
  const activityPanel =
    (formatGenBanner && robotJob?.key === 'multiformat') || robotJob?.key === 'collect' ? (
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
        collecting={isBusy('collect')}
        collectRunning={robotJob?.key === 'collect'}
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
            top10={top10}
            onUseSuggestion={useArticleInFlow}
            onRefreshTop10={() => fetchTop10({ persist: true })}
            onPatrol={runAgenticSearch}
            loadingTop10={loading}
            isSearching={isSearching}
            top10Error={top10Error}
            adTrendNotes={adTrendNotes}
            adTrendMessage={adTrendMessage}
            adTrendBusy={adTrendBusy}
            onRefreshAdTrendNotes={fetchAdTrendNotes}
            onGenerateAdTrendNotes={generateAdTrendNotes}
            onGenerateAdNoteImage={generateAdNoteImage}
            onOpenSources={() => goToTab('profile')}
            signalsCount={articlesTotalHint ?? articles?.length ?? 0}
            flowCounts={{
              discover: articlesTotalHint ?? articles?.length ?? top10?.length ?? 0,
              create: allPieces.length,
              review:
                allPieces.filter((p) => p.status === 'pending_approval').length +
                (pendingBlogPosts || []).filter((p) => p.status === 'pending' || p.status === 'pending_approval').length,
              distribute: (publishedBlogPosts || []).length,
            }}
            intelligenceBusy={
              Boolean(isBusy?.('collect') || robotJob?.key === 'collect' || loading || isSearching || adTrendBusy)
            }
            onRefreshIntelligence={async () => {
              try {
                await triggerIngest();
              } catch {
                /* ingest may notify itself */
              }
              await Promise.allSettled([
                fetchTop10({ persist: true }),
                generateAdTrendNotes(),
              ]);
            }}
            onOpenLive={() => goToTab('live')}
          />
        )}

        {/* TAB 9: AI GATEWAY & MÉTRICAS (FASE 5) */}
        {activeTab === 'aigateway' && (
          <AIHubTab
            loading={loading}
            isBusy={isBusy}
            aiUsageStats={aiUsageStats}
            aiProviders={aiProviders}
            aiStatsError={aiStatsError}
            newProvider={newProvider}
            setNewProvider={setNewProvider}
            testPrompt={testPrompt}
            setTestPrompt={setTestPrompt}
            testResult={testResult}
            onRefreshModels={fetchAiStats}
            onCreateProvider={createAiProvider}
            onUpdateProvider={updateAiProvider}
            onRemoveProvider={removeAiProvider}
            onRunTest={runGatewayTest}
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
            onRefreshAgents={fetchAgentsCatalog}
            onRunPipeline={runAgentsPipeline}
            onRunNamed={runNamedAgent}
          />
        )}

        {activeTab === 'multiformat' && (
          <MultiFormatTab
            selectedArticleForApproval={selectedArticleForApproval}
            selectedLanguage={selectedLanguage}
            onLanguageChange={changeFormatLanguage}
            providerMode={providerMode}
            onProviderModeChange={(mode) => {
              setProviderMode(mode);
              if (mode === 'cloud' || mode === 'auto') {
                ensureAiProviders({ force: true });
              }
            }}
            aiProviders={aiProviders}
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
            parseCarouselJson={parseCarouselJson}
            goToTab={goToTab}
            updateContentPiece={updateContentPiece}
            profile={profile}
            pendingBlogPosts={pendingBlogPosts}
            publishedBlogPosts={publishedBlogPosts}
            editorialBlogPosts={editorialBlogPosts}
            onGenerateBlog={generateStudioBlogDraft}
            onApproveBlog={approvePendingBlog}
            onPublishBlog={publishPendingBlog}
            blogBusy={isBusy('blog')}
            onImagesGenerated={(data) => {
              if (!data) return;
              setMultiFormatContent((prev) => {
                if (!prev) return prev;
                const next = { ...prev };
                if (Array.isArray(data.slides)) {
                  next.carousel_slides = data.slides;
                }
                if (data.piece) {
                  next.pieces = (prev.pieces || []).map((p) =>
                    p.id === data.piece_id || p.id === data.piece.id
                      ? { ...p, ...data.piece, creatives: data.piece.creatives || data }
                      : p
                  );
                }
                return next;
              });
            }}
          />
        )}

        {activeTab === 'profile' && (
          <ProfileTab
            profile={profile}
            pillarDrafts={pillarDrafts}
            setPillarDrafts={setPillarDrafts}
            saveProfilePercentages={saveProfilePercentages}
            themeDrafts={themeDrafts}
            setThemeDrafts={setThemeDrafts}
            saveSearchThemes={saveSearchThemes}
            resetSearchThemes={resetSearchThemes}
            applyPdfPillarMix={applyPdfPillarMix}
            pctRecommendation={pctRecommendation}
            pctRecMessage={pctRecMessage}
            pctRecLoading={pctRecLoading}
            onLoadPctRecommendation={() => fetchPctRecommendation(false)}
            onGeneratePctRecommendation={() => fetchPctRecommendation(true)}
            onAcceptPctRecommendation={acceptPctRecommendation}
            onRejectPctRecommendation={rejectPctRecommendation}
          />
        )}

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
            fetchError={articlesError}
            onFetchArticles={fetchArticles}
            onUseInFlow={useArticleInFlow}
            workedArticleIds={workedArticleIdSet}
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
