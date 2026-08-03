import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Cpu,
  Home,
  Layers,
  LogOut,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  ShieldCheck,
  User,
} from 'lucide-react';

const SIDEBAR_KEY = 'a360_sidebar_open';

const NAV_GROUPS = [
  {
    title: 'Dashboard',
    items: [
      ['hoy', 'Hoy', Home],
      ['live', 'Noticias en vivo', Newspaper],
      ['multisynthesis', 'Síntesis Multinoticia', Layers],
    ],
  },
  {
    title: 'Configuración',
    items: [
      ['profile', 'Perfil', User],
      ['aigateway', 'Inteligencia Artificial', Cpu],
    ],
  }
];

const ALL_ITEMS = NAV_GROUPS.flatMap(g => g.items);

const TITLES = {
  ...Object.fromEntries(ALL_ITEMS.map(([id, label]) => [id, label])),
  multiformat: 'Estudio de contenido',
  multisynthesis: 'Síntesis Multinoticia con Foco Único',
};

const FLOW_STEPS = [
  ['hoy', 'Descubrir'],
  ['multiformat', 'Crear'],
  ['multiformat', 'Revisar'],
  ['multiformat', 'Distribuir'],
];

const SUBTITLES = {
  hoy: 'Prioriza una señal y llévala a producción.',
  live: 'Explora y filtra el inventario editorial.',
  multisynthesis: 'Recibe un solo artículo fusionado a partir del mejor foco, sin seleccionar noticias.',
  multiformat: 'Convierte una noticia en piezas, creatividades y distribución.',
  profile: 'Define el enfoque editorial y los temas que alimentan el sistema.',
  aigateway: 'Configura los motores que asisten la operación editorial.',
};

function NavButton({ id, label, Icon, active, onNavigate }) {
  return (
    <button
      type="button"
      className={`sidebar-link ${active ? 'active' : ''}`}
      onClick={() => onNavigate(id)}
      aria-current={active ? 'page' : undefined}
      aria-label={label}
    >
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}

export default function AppShell({
  activeTab,
  onNavigate,
  userEmail,
  healthInfo,
  onCollect,
  collecting,
  collectRunning = false,
  onLogout,
  activity,
  workflow,
  children,
}) {

  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      const stored = localStorage.getItem(SIDEBAR_KEY);
      return stored === null ? true : stored === '1';
    } catch {
      return true;
    }
  });
  const [isMobileNav, setIsMobileNav] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_KEY, sidebarOpen ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, [sidebarOpen]);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined;
    const mq = window.matchMedia('(max-width: 640px)');
    const sync = () => setIsMobileNav(mq.matches);
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  }, []);

  const collectBusy = collecting || collectRunning;
  const flowIndex = activeTab === 'hoy' || activeTab === 'live'
    ? 0
    : activeTab === 'multiformat'
      ? 1
      : -1;

  const toggleSidebar = () => setSidebarOpen((open) => !open);
  const navVisible = sidebarOpen || isMobileNav;
  const shellCollapsed = !sidebarOpen && !isMobileNav;

  const collectLabel = collecting
    ? 'Iniciando…'
    : collectRunning
      ? 'Recolectando…'
      : 'Actualizar fuentes';
  const collectLabelShort = collecting
    ? 'Iniciando…'
    : collectRunning
      ? 'Recolectando…'
      : 'Actualizar';

  return (
    <div className={`app-shell ${shellCollapsed ? 'is-sidebar-collapsed' : ''}`.trim()}>
      <aside
        className="app-sidebar"
        aria-label="Navegación principal"
        hidden={!navVisible}
      >
        <div className="app-brand">
          <span className="app-brand-mark" aria-hidden="true">
            <ShieldCheck size={20} />
          </span>
          <div>
            <strong>Autoridad 360</strong>
            <span>Flujo editorial</span>
          </div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={toggleSidebar}
            aria-expanded={sidebarOpen}
            aria-controls="app-sidebar-panel"
            title="Ocultar menú"
            aria-label="Ocultar menú lateral"
          >
            <PanelLeftClose size={18} aria-hidden="true" />
          </button>
        </div>

        <nav className="sidebar-nav" id="app-sidebar-panel">
          {NAV_GROUPS.map((group, idx) => (
            <div key={idx} className="sidebar-group">
              <span className="sidebar-group-label">{group.title}</span>
              {group.items.map(([id, label, Icon]) => (
                <NavButton
                  key={id}
                  id={id}
                  label={label}
                  Icon={Icon}
                  active={activeTab === id}
                  onNavigate={onNavigate}
                />
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-account">
          <span className="sidebar-account-label">Sesión activa</span>
          <span className="sidebar-account-email" title={userEmail}>
            {userEmail}
          </span>
          <button type="button" className="sidebar-logout" onClick={onLogout} aria-label="Cerrar sesión">
            <LogOut size={15} aria-hidden="true" />
            <span className="sidebar-logout-label">Cerrar sesión</span>
          </button>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="workspace-header">
          <div className="workspace-heading">
            {!navVisible && (
              <button
                type="button"
                className="sidebar-toggle sidebar-toggle--open"
                onClick={toggleSidebar}
                aria-expanded={false}
                title="Mostrar menú"
                aria-label="Mostrar menú lateral"
              >
                <PanelLeftOpen size={18} aria-hidden="true" />
              </button>
            )}
            <div>
              <span className="workspace-eyebrow">Autoridad 360 · operación editorial</span>
              <h1>{TITLES[activeTab] || 'Autoridad 360'}</h1>
              <p className="workspace-subtitle">{SUBTITLES[activeTab] || 'Gestiona el ciclo editorial.'}</p>
            </div>
          </div>
          <div className="workspace-actions">
            {activeTab !== 'hoy' && (
              <button
                type="button"
                className="btn btn-secondary workspace-back"
                onClick={() => onNavigate('hoy')}
                title="Volver a Hoy"
                aria-label="Volver a Hoy"
              >
                <ArrowLeft size={16} aria-hidden="true" />
                <span>Volver a Hoy</span>
              </button>
            )}
            <button
              type="button"
              className="btn btn-primary"
              onClick={onCollect}
              disabled={collecting}
              title={
                collectRunning
                  ? 'Recolección en segundo plano (puedes seguir trabajando)'
                  : 'Actualizar feeds RSS'
              }
            >
              <RefreshCw
                size={16}
                className={collectBusy ? 'animate-spin' : ''}
                aria-hidden="true"
              />
              <span className="workspace-cta-full">{collectLabel}</span>
              <span className="workspace-cta-short">{collectLabelShort}</span>
            </button>
          </div>
        </header>

        {flowIndex >= 0 && activeTab !== 'hoy' && (
          <nav className="editorial-flow" aria-label="Progreso del flujo editorial">
            {FLOW_STEPS.map(([id, label], index) => (
              <button
                key={`${id}-${label}`}
                type="button"
                className={`editorial-flow-step ${index === flowIndex ? 'is-current' : index < flowIndex ? 'is-complete' : ''}`}
                onClick={() => index === 0 && onNavigate('hoy')}
                disabled={index > flowIndex}
              >
                <span>{index + 1}</span>
                {label}
              </button>
            ))}
          </nav>
        )}

        {activity}
        {workflow}

        <main className="workspace-content" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
