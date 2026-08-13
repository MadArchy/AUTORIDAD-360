/**
 * AUTORIDAD 360 — ESTADO LOCAL Y PERSISTENCIA (LocalStorage)
 * Gestiona el perfil de Juan Vásquez, pilares editoriales, piezas guardadas y configuración.
 */

const STORAGE_KEYS = {
  PROFILE: 'a360_profile_v1',
  PILLARS: 'a360_pillars_v1',
  ARTICLES: 'a360_articles_v1',
  SYNTHESES: 'a360_syntheses_v1',
  PACKAGES: 'a360_packages_v1',
  AI_CONFIG: 'a360_ai_config_v1',
  CALENDAR: 'a360_calendar_v1',
  METRICS: 'a360_metrics_v1',
  WORKED_ARTICLES: 'a360_worked_articles',
};

// Perfil inicial de Autoridad para Juan Vásquez
const DEFAULT_PROFILE = {
  name: 'Juan Vásquez',
  title: 'Especialista en IA Aplicada, Estrategia Legal & Transformación Digital',
  bio: 'Líder de opinión y estratega que asesora a corporativos y directivos en la adopción responsable y rentable de inteligencia artificial, marcos de gobernanza y posicionamiento de autoridad.',
  target_audiences: [
    'Directores Generales (CEOs) y Miembros de Consejo',
    'Directores de Tecnología (CTOs / CIOs)',
    'Directores Legales (CLOs) y Socios de Firmas',
    'Fundadores de Startups Tech y Emprendedores B2B'
  ],
  services: [
    'Consultoría Estratégica en IA y Regulación',
    'Capacitaciones Ejecutivas y Masterclasses In-Company',
    'Desarrollo de Marcas Personales de Autoridad 360'
  ],
  markets: [
    { code: 'MX', name: 'México', target_pct: 50 },
    { code: 'US', name: 'Estados Unidos (Hispanos/Bilingüe)', target_pct: 30 },
    { code: 'LATAM', name: 'Colombia, Chile, Perú', target_pct: 20 }
  ]
};

// Pilares Editoriales Canónicos
const DEFAULT_PILLARS = [
  {
    id: 1,
    name: 'Gobernanza & Regulación de IA',
    slug: 'gobernanza-ia',
    description: 'Leyes, marcos éticos, cumplimiento normativo (EU AI Act, México, USA) y mitigación de riesgos corporativos.',
    target_pct: 35,
    current_count: 14,
    color: '#6366f1'
  },
  {
    id: 2,
    name: 'IA Aplicada al Negocio B2B',
    slug: 'ia-negocio',
    description: 'Casos de uso reales, ROI de automatización, agentes autónomos y transformación operativa.',
    target_pct: 30,
    current_count: 11,
    color: '#06b6d4'
  },
  {
    id: 3,
    name: 'Autoridad Digital & Marca Personal',
    slug: 'autoridad-marca',
    description: 'Estrategias de posicionamiento ejecutivo, creación de contenido de alto valor y captación de clientes de alto ticket.',
    target_pct: 20,
    current_count: 7,
    color: '#10b981'
  },
  {
    id: 4,
    name: 'Tendencias & Futuro del Trabajo',
    slug: 'tendencias-futuro',
    description: 'Impacto en el empleo directivo, habilidades de la nueva era y prospectiva tecnológica.',
    target_pct: 15,
    current_count: 4,
    color: '#f59e0b'
  }
];

// Configuración de Proveedores de IA
const DEFAULT_AI_CONFIG = {
  active_provider: 'autonomous', // autonomous | groq | openai | gemini | anthropic | ollama
  ollama_url: 'http://localhost:11434',
  ollama_model: 'gemma4:e2b',
  groq_key: '',
  groq_model: 'llama-3.3-70b-versatile',
  openai_key: '',
  openai_model: 'gpt-4o',
  gemini_key: '',
  gemini_model: 'gemini-1.5-flash',
  anthropic_key: '',
  anthropic_model: 'claude-3-5-sonnet-20241022',
  temperature: 0.7
};

class StateManager {
  constructor() {
    this.profile = this.load(STORAGE_KEYS.PROFILE, DEFAULT_PROFILE);
    this.pillars = this.load(STORAGE_KEYS.PILLARS, DEFAULT_PILLARS);
    this.aiConfig = this.load(STORAGE_KEYS.AI_CONFIG, DEFAULT_AI_CONFIG);
    this.syntheses = this.load(STORAGE_KEYS.SYNTHESES, []);
    this.packages = this.load(STORAGE_KEYS.PACKAGES, []);
    this.workedArticleIds = new Set(this.load(STORAGE_KEYS.WORKED_ARTICLES, []));
    this.calendar = this.load(STORAGE_KEYS.CALENDAR, []);
    this.metrics = this.load(STORAGE_KEYS.METRICS, {
      total_articles_analyzed: 142,
      pieces_generated: 28,
      leads_qualified: 19,
      conversion_rate: '13.4%'
    });
  }

  load(key, fallback) {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : fallback;
    } catch (e) {
      console.warn(`[StateManager] Error loading ${key}:`, e);
      return fallback;
    }
  }

  save(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error(`[StateManager] Error saving ${key}:`, e);
    }
  }

  saveProfile(updated) {
    this.profile = { ...this.profile, ...updated };
    this.save(STORAGE_KEYS.PROFILE, this.profile);
  }

  savePillars(updatedPillars) {
    this.pillars = updatedPillars;
    this.save(STORAGE_KEYS.PILLARS, this.pillars);
  }

  saveAiConfig(updated) {
    this.aiConfig = { ...this.aiConfig, ...updated };
    this.save(STORAGE_KEYS.AI_CONFIG, this.aiConfig);
  }

  addSynthesis(synthesis) {
    this.syntheses.unshift(synthesis);
    this.save(STORAGE_KEYS.SYNTHESES, this.syntheses);
    this.metrics.pieces_generated += 1;
    this.save(STORAGE_KEYS.METRICS, this.metrics);
  }

  addPackage(pkg) {
    this.packages.unshift(pkg);
    this.save(STORAGE_KEYS.PACKAGES, this.packages);
  }

  markArticleWorked(id) {
    this.workedArticleIds.add(id);
    this.save(STORAGE_KEYS.WORKED_ARTICLES, Array.from(this.workedArticleIds));
  }

  // Calcula qué pilar tiene mayor déficit porcentual vs meta
  getDeficitPillar() {
    const totalPieces = this.pillars.reduce((acc, p) => acc + (p.current_count || 0), 0) || 1;
    let maxDeficit = -999;
    let deficitPillar = this.pillars[0];

    this.pillars.forEach(p => {
      const currentPct = Math.round(((p.current_count || 0) / totalPieces) * 100);
      const targetPct = p.target_pct || 25;
      const deficit = targetPct - currentPct;
      if (deficit > maxDeficit) {
        maxDeficit = deficit;
        deficitPillar = p;
      }
    });

    return { pillar: deficitPillar, deficit: maxDeficit };
  }

  // Incrementa el conteo de piezas de un pilar cuando se aprueba
  incrementPillarCount(pillarSlug) {
    const updated = this.pillars.map(p => {
      if (p.slug === pillarSlug) {
        return { ...p, current_count: (p.current_count || 0) + 1 };
      }
      return p;
    });
    this.savePillars(updated);
  }

  // Auto-agenda el paquete generado en el calendario editorial
  schedulePackageToCalendar(pkg, pillarName) {
    const today = new Date();
    const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'];
    
    const events = [
      { id: Date.now() + 1, day: 'Lunes', time: '08:30 AM', format: 'Ensayo / Post Largo', title: pkg.topic, status: 'approved', pillar: pillarName },
      { id: Date.now() + 2, day: 'Miércoles', time: '11:00 AM', format: 'Carrusel de 5 Slides', title: `Carrusel: ${pkg.topic}`, status: 'scheduled', pillar: pillarName },
      { id: Date.now() + 3, day: 'Jueves', time: '06:00 PM', format: 'Guion de Video', title: `Video: ${pkg.topic}`, status: 'scheduled', pillar: pillarName },
      { id: Date.now() + 4, day: 'Viernes', time: '09:00 AM', format: 'Newsletter Semanal', title: `Boletín: ${pkg.topic}`, status: 'scheduled', pillar: pillarName },
    ];

    this.calendar = [...events, ...this.calendar.slice(0, 8)];
    this.save(STORAGE_KEYS.CALENDAR, this.calendar);
    return events;
  }

  exportBackup() {
    const backup = {
      profile: this.profile,
      pillars: this.pillars,
      aiConfig: { ...this.aiConfig, groq_key: '', openai_key: '', gemini_key: '' }, // Omit keys in export for safety
      syntheses: this.syntheses,
      packages: this.packages,
      calendar: this.calendar,
      metrics: this.metrics,
      timestamp: new Date().toISOString()
    };
    return JSON.stringify(backup, null, 2);
  }

  importBackup(jsonString) {
    try {
      const parsed = JSON.parse(jsonString);
      if (parsed.profile) this.saveProfile(parsed.profile);
      if (parsed.pillars) this.savePillars(parsed.pillars);
      if (parsed.syntheses) {
        this.syntheses = parsed.syntheses;
        this.save(STORAGE_KEYS.SYNTHESES, this.syntheses);
      }
      return true;
    } catch (e) {
      console.error('Error importing backup:', e);
      return false;
    }
  }
}

window.AppState = new StateManager();

