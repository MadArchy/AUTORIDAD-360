/**
 * AUTORIDAD 360 — MÓDULO DE NOTICIAS EN VIVO Y RSS
 * Captura noticias de tecnología, negocios e IA en tiempo real o usa el inventario local.
 */

const RSS_FEEDS = [
  { name: 'Google News IA', url: 'https://news.google.com/rss/search?q=inteligencia+artificial+empresas&hl=es-419&gl=MX&ceid=MX:es-419', pillar: 'ia-negocio' },
  { name: 'Gobernanza Tech', url: 'https://news.google.com/rss/search?q=regulacion+inteligencia+artificial+ley&hl=es-419&gl=MX&ceid=MX:es-419', pillar: 'gobernanza-ia' },
  { name: 'El Economista Tech', url: 'https://www.eleconomista.com.mx/rss/tecnologia.xml', pillar: 'ia-negocio' }
];

const SEED_ARTICLES = [
  {
    id: 101,
    title: 'La Unión Europea aprueba el reglamento final del AI Act con sanciones de hasta 35M€',
    source: 'Financial Times / Tech Law',
    published_at: 'Hace 2 horas',
    url: 'https://ec.europa.eu/commission/presscorner/detail/es/ip_24_88',
    pillar_slug: 'gobernanza-ia',
    pillar_name: 'Gobernanza & Regulación de IA',
    score: 98,
    snippet: 'Las corporaciones con modelos fundacionales de alto riesgo deberán presentar auditorías de seguridad algorítmica y mapas de transparencia de datos de entrenamiento.'
  },
  {
    id: 102,
    title: 'Estudio de McKinsey revela que el 65% de las empresas Fortune 500 ya implementan agentes autónomos',
    source: 'McKinsey Insights',
    published_at: 'Hace 4 horas',
    url: 'https://www.mckinsey.com/capabilities/quantumblack/our-insights',
    pillar_slug: 'ia-negocio',
    pillar_name: 'IA Aplicada al Negocio B2B',
    score: 95,
    snippet: 'La automatización de procesos analíticos y de atención B2B reduce los costos operativos en un 32% en el primer semestre de implementación.'
  },
  {
    id: 103,
    title: 'Cómo los CEOs utilizan su marca personal en LinkedIn para captar rondas de inversión y contratos B2B',
    source: 'Harvard Business Review',
    published_at: 'Hace 6 horas',
    url: 'https://hbr.org/topic/personal-branding',
    pillar_slug: 'autoridad-marca',
    pillar_name: 'Autoridad Digital & Marca Personal',
    score: 92,
    snippet: 'Los directores con presencia editorial activa generan 4.5 veces más confianza en comités de compra que empresas que dependen únicamente de pauta publicitaria.'
  },
  {
    id: 104,
    title: 'El Senado de EE.UU. presenta proyecto bipartidista de responsabilidad civil para desarrolladores de LLMs',
    source: 'Reuters Legal',
    published_at: 'Hace 8 horas',
    url: 'https://www.reuters.com/technology/ai-regulation',
    pillar_slug: 'gobernanza-ia',
    pillar_name: 'Gobernanza & Regulación de IA',
    score: 90,
    snippet: 'La propuesta legal busca eliminar la inmunidad frente a sesgos algorítmicos y daños comerciales provocados por alucinaciones en software crítico.'
  },
  {
    id: 105,
    title: 'El auge del Chief AI Officer: Las empresas reorganizan su C-Suite para liderar la adopción',
    source: 'Forbes Executive',
    published_at: 'Hace 12 horas',
    url: 'https://www.forbes.com/leadership',
    pillar_slug: 'tendencias-futuro',
    pillar_name: 'Tendencias & Futuro del Trabajo',
    score: 88,
    snippet: 'Más del 40% de los conglomerados en América Latina planean crear la figura de Director de IA antes del cierre del año fiscal.'
  },
  {
    id: 106,
    title: 'Bancos latinoamericanos implementan modelos locales de lenguaje para análisis de riesgo crediticio',
    source: 'América Economía',
    published_at: 'Hace 1 día',
    url: 'https://www.americaeconomia.com',
    pillar_slug: 'ia-negocio',
    pillar_name: 'IA Aplicada al Negocio B2B',
    score: 87,
    snippet: 'El uso de modelos on-premise y privacidad estricta permite a las entidades financieras cumplir con la regulación bancaria local mientras automatizan auditorías.'
  }
];

class NewsService {
  constructor() {
    this.articles = [...SEED_ARTICLES];
    this.selectedArticleIds = new Set();
  }

  async fetchLiveNews() {
    try {
      const feedPromises = RSS_FEEDS.map(async (feed) => {
        const proxyUrl = `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(feed.url)}`;
        const res = await fetch(proxyUrl);
        if (!res.ok) return [];
        const data = await res.json();
        if (data.status !== 'ok' || !data.items) return [];

        return data.items.map((item, idx) => ({
          id: Date.now() + idx + Math.floor(Math.random() * 1000),
          title: item.title,
          source: item.author || feed.name,
          published_at: new Date(item.pubDate).toLocaleDateString('es-MX', { hour: '2-digit', minute: '2-digit' }),
          url: item.link,
          pillar_slug: feed.pillar,
          pillar_name: window.AppState.pillars.find(p => p.slug === feed.pillar)?.name || 'General',
          score: 85 + (idx % 12),
          snippet: item.description?.replace(/<[^>]+>/g, '').slice(0, 180) + '...'
        }));
      });

      const results = await Promise.allSettled(feedPromises);
      const newItems = results
        .filter(r => r.status === 'fulfilled')
        .flatMap(r => r.value);

      if (newItems.length > 0) {
        // Unir evitando duplicados por título
        const existingTitles = new Set(this.articles.map(a => a.title.toLowerCase()));
        const uniqueNew = newItems.filter(item => !existingTitles.has(item.title.toLowerCase()));
        this.articles = [...uniqueNew, ...this.articles];
      }
      return this.articles;
    } catch (err) {
      console.warn('[NewsService] Usando fallback local:', err);
      return this.articles;
    }
  }

  getArticles(filterPillar = '', query = '') {
    return this.articles.filter(a => {
      const matchPillar = !filterPillar || a.pillar_slug === filterPillar;
      const matchQuery = !query || 
        a.title.toLowerCase().includes(query.toLowerCase()) || 
        a.snippet.toLowerCase().includes(query.toLowerCase());
      return matchPillar && matchQuery;
    });
  }

  getTopNewsForPillar(pillarSlug, limit = 2) {
    const matching = this.articles.filter(a => a.pillar_slug === pillarSlug);
    if (matching.length === 0) return this.articles.slice(0, limit);
    return matching.sort((a, b) => b.score - a.score).slice(0, limit);
  }

  toggleSelect(id) {

    if (this.selectedArticleIds.has(id)) {
      this.selectedArticleIds.delete(id);
    } else {
      if (this.selectedArticleIds.size >= 5) {
        throw new Error('Puedes seleccionar un máximo de 5 noticias para una síntesis.');
      }
      this.selectedArticleIds.add(id);
    }
    return this.getSelectedArticles();
  }

  clearSelection() {
    this.selectedArticleIds.clear();
  }

  getSelectedArticles() {
    return this.articles.filter(a => this.selectedArticleIds.has(a.id));
  }
}

window.NewsService = new NewsService();
