import React, { useEffect, useState } from 'react';
import {
  Activity,
  BookOpen,
  Building2,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileText,
  Home,
  LogOut,
  Megaphone,
  Newspaper,
  RefreshCw,
  Send,
  ShieldCheck,
  User,
} from 'lucide-react';

const NAV_GROUPS = [
  {
    title: 'Dashboard',
    items: [
      ['hoy', 'Hoy', Home],
      ['live', 'Noticias en vivo', Newspaper],
    ],
  },
  {
    title: 'Distribución',
    items: [
      ['publish', 'Publicar', Send],
      ['blog', 'Blog', BookOpen],
      ['marketing', 'Marketing', Megaphone],
    ],
  },
  {
    title: 'Configuración',
    items: [
      ['profile', 'Perfil', User],
      ['multiempresa', 'Organización', Building2],
      ['aigateway', 'Inteligencia Artificial', Cpu],
      ['report', 'Reportes', FileText],
    ],
  }
];

const ALL_ITEMS = NAV_GROUPS.flatMap(g => g.items);

const TITLES = {
  ...Object.fromEntries(ALL_ITEMS.map(([id, label]) => [id, label])),
  multiformat: 'Generar Formatos',
};

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
  collectRunning = false,
  onLogout,
  activity,
  workflow,
  children,
}) {

  const collectBusy = collecting || collectRunning;

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
              {collecting
                ? 'Iniciando…'
                : collectRunning
                  ? 'Recolectando…'
                  : 'Actualizar fuentes'}
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
