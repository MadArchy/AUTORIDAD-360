import React, { useEffect, useState } from 'react';
import {
  Activity,
  BarChart2,
  BookOpen,
  Bot,
  Building2,
  Calendar,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileText,
  Home,
  LogOut,
  Megaphone,
  Newspaper,
  RefreshCw,
  Scale,
  Send,
  ShieldCheck,
  TrendingUp,
  User,
} from 'lucide-react';

const PRIMARY_NAV = [
  ['hoy', 'Hoy', Home],
  ['top10', 'Elegir', BarChart2],
  ['approval', 'Aprobar', ShieldCheck],
  ['publish', 'Publicar', Send],
];

const MORE_NAV = [
  ['live', 'Noticias', Newspaper],
  ['ops', 'Calendario', Calendar],
  ['refresh', 'Refresh', RefreshCw],
  ['blog', 'Blog', BookOpen],
  ['legalseo', 'SEO / Legal', Scale],
  ['marketing', 'Marketing', Megaphone],
  ['report', 'Reportes', FileText],
  ['metrics', 'Resultados', TrendingUp],
  ['profile', 'Perfil', User],
  ['aigateway', 'Modelos de IA', Cpu],
  ['agents', 'Agentes', Bot],
  ['multiempresa', 'Organización', Building2],
];

const TITLES = {
  ...Object.fromEntries([...PRIMARY_NAV, ...MORE_NAV].map(([id, label]) => [id, label])),
  // Destino tras “Usar esta noticia”; no es ítem del menú.
  multiformat: 'Generar formatos',
};

const MORE_IDS = new Set(MORE_NAV.map(([id]) => id));

function NavButton({ id, label, Icon, active, onNavigate }) {
  return (
    <button
      type="button"
      className={`sidebar-link ${active ? 'active' : ''}`}
      onClick={() => onNavigate(id)}
      aria-current={active ? 'page' : undefined}
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
  onLogout,
  activity,
  workflow,
  children,
}) {
  const [moreOpen, setMoreOpen] = useState(() => MORE_IDS.has(activeTab));

  useEffect(() => {
    if (MORE_IDS.has(activeTab)) setMoreOpen(true);
  }, [activeTab]);

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="Navegación principal">
        <div className="app-brand">
          <span className="app-brand-mark" aria-hidden="true">
            <ShieldCheck size={20} />
          </span>
          <div>
            <strong>Autoridad 360</strong>
            <span>Flujo editorial</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-group">
            <span className="sidebar-group-label">Ciclo diario</span>
            {PRIMARY_NAV.map(([id, label, Icon]) => (
              <NavButton
                key={id}
                id={id}
                label={label}
                Icon={Icon}
                active={
                  activeTab === id ||
                  (id === 'top10' && activeTab === 'multiformat')
                }
                onNavigate={onNavigate}
              />
            ))}
          </div>

          <div className="sidebar-group sidebar-group-more">
            <button
              type="button"
              className="sidebar-more-toggle"
              onClick={() => setMoreOpen((v) => !v)}
              aria-expanded={moreOpen}
            >
              {moreOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
              <span>Más herramientas</span>
            </button>
            {moreOpen &&
              MORE_NAV.map(([id, label, Icon]) => (
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
        </nav>

        <div className="sidebar-account">
          <span className="sidebar-account-label">Sesión activa</span>
          <span className="sidebar-account-email" title={userEmail}>
            {userEmail}
          </span>
          <button type="button" className="sidebar-logout" onClick={onLogout}>
            <LogOut size={15} aria-hidden="true" /> Cerrar sesión
          </button>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="workspace-header">
          <div>
            <span className="workspace-eyebrow">Workspace editorial</span>
            <h1>{TITLES[activeTab] || 'Autoridad 360'}</h1>
          </div>
          <div className="workspace-actions">
            <span
              className={`system-status ${healthInfo?.status === 'ok' ? 'is-online' : 'is-warning'}`}
              title={`Entorno: ${healthInfo?.app_env || 'desconocido'}`}
            >
              <Activity size={14} aria-hidden="true" />
              {healthInfo?.db_dialect || 'Sistema'} · {healthInfo?.status || 'verificando'}
            </span>
            <button
              type="button"
              className="btn btn-primary"
              onClick={onCollect}
              disabled={collecting}
            >
              <RefreshCw
                size={16}
                className={collecting ? 'animate-spin' : ''}
                aria-hidden="true"
              />
              {collecting ? 'Recolectando…' : 'Actualizar fuentes'}
            </button>
          </div>
        </header>

        {activity}
        {workflow}

        <main className="workspace-content" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
