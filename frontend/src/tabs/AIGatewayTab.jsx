import React, { useEffect, useMemo, useState } from 'react';
import { RefreshCw, Zap, Cpu, AlertTriangle, DollarSign, Sparkles, Send, ChevronDown, ChevronUp, KeyRound } from 'lucide-react';
import { api } from '../api';

const PROVIDER_PRESETS = {
  openai: {
    label: 'OpenAI',
    name: 'OpenAI',
    model_name: 'gpt-4o',
    base_url: 'https://api.openai.com/v1',
    priority: 20,
    needsKey: true,
    hint: 'Pega tu API key de platform.openai.com',
  },
  anthropic: {
    label: 'Anthropic',
    name: 'Anthropic',
    model_name: 'claude-3-5-sonnet-20240620',
    base_url: 'https://api.anthropic.com/v1',
    priority: 30,
    needsKey: true,
    hint: 'Pega tu API key de console.anthropic.com',
  },
  gemini: {
    label: 'Gemini',
    name: 'Gemini',
    model_name: 'gemini-1.5-pro',
    base_url: 'https://generativelanguage.googleapis.com/v1beta',
    priority: 40,
    needsKey: true,
    hint: 'Pega tu API key de Google AI Studio',
  },
  ollama: {
    label: 'Ollama (local)',
    name: 'Ollama Local',
    model_name: 'llama3.1',
    base_url: 'http://localhost:11434',
    priority: 10,
    needsKey: false,
    hint: 'Sin API key. Usa el Ollama que ya corre en tu máquina.',
  },
};

/** Fallback local si /ai/models aún no tiene filas. */
const MODEL_FALLBACKS = {
  openai: [
    { model_key: 'gpt-5', display_name: 'GPT-5' },
    { model_key: 'gpt-5-mini', display_name: 'GPT-5 mini' },
    { model_key: 'gpt-4.1', display_name: 'GPT-4.1' },
    { model_key: 'gpt-4.1-mini', display_name: 'GPT-4.1 mini' },
    { model_key: 'gpt-4o', display_name: 'GPT-4o' },
    { model_key: 'gpt-4o-mini', display_name: 'GPT-4o mini' },
    { model_key: 'o3', display_name: 'o3' },
    { model_key: 'o4-mini', display_name: 'o4-mini' },
  ],
  anthropic: [
    { model_key: 'claude-sonnet-4-20250514', display_name: 'Claude Sonnet 4' },
    { model_key: 'claude-opus-4-20250514', display_name: 'Claude Opus 4' },
    { model_key: 'claude-3-5-sonnet-20240620', display_name: 'Claude 3.5 Sonnet' },
    { model_key: 'claude-3-5-haiku-20241022', display_name: 'Claude 3.5 Haiku' },
  ],
  gemini: [
    { model_key: 'gemini-2.5-pro', display_name: 'Gemini 2.5 Pro' },
    { model_key: 'gemini-2.5-flash', display_name: 'Gemini 2.5 Flash' },
    { model_key: 'gemini-2.0-flash', display_name: 'Gemini 2.0 Flash' },
    { model_key: 'gemini-1.5-pro', display_name: 'Gemini 1.5 Pro' },
    { model_key: 'gemini-1.5-flash', display_name: 'Gemini 1.5 Flash' },
  ],
  ollama: [
    { model_key: 'llama3.1', display_name: 'Llama 3.1' },
    { model_key: 'mistral', display_name: 'Mistral' },
    { model_key: 'qwen2.5', display_name: 'Qwen 2.5' },
  ],
};

const CUSTOM_MODEL = '__custom__';

const fieldStyle = {
  padding: '10px 12px',
  borderRadius: 8,
  background: 'rgba(0,0,0,0.35)',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.15)',
  width: '100%',
  boxSizing: 'border-box',
};

function ModelListPicker({ options, value, onChange, open, setOpen, label, isCustom = false }) {
  const currentLabel = isCustom
    ? 'Otro (escribir…)'
    : options.find((m) => m.model_key === value)?.display_name || value || 'Elegir modelo…';

  return (
    <div style={{ position: 'relative', marginBottom: 8 }}>
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => setOpen(!open)}
        style={{
          width: '100%',
          justifyContent: 'space-between',
          textAlign: 'left',
          color: '#fff',
          background: 'rgba(0,0,0,0.45)',
          border: '1px solid rgba(255,255,255,0.2)',
        }}
        aria-expanded={open}
        aria-label={label || 'Elegir modelo'}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {currentLabel}
        </span>
        <span style={{ opacity: 0.7, marginLeft: 8 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div
          role="listbox"
          style={{
            marginTop: 6,
            maxHeight: 260,
            overflowY: 'auto',
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.22)',
            background: '#0f141b',
            boxShadow: '0 12px 28px rgba(0,0,0,0.55)',
            zIndex: 50,
            position: 'relative',
          }}
        >
          {options.map((m) => {
            const active = !isCustom && m.model_key === value;
            return (
              <button
                key={m.model_key}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(m.model_key);
                  setOpen(false);
                }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '10px 12px',
                  border: 'none',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                  background: active ? 'rgba(108,156,242,0.25)' : 'transparent',
                  color: '#f4f6f8',
                  cursor: 'pointer',
                  fontSize: '0.88rem',
                }}
              >
                {m.display_name}
                <span style={{ display: 'block', fontSize: '0.72rem', color: '#9aa3b2' }}>
                  {m.model_key}
                </span>
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => {
              onChange(CUSTOM_MODEL);
              setOpen(false);
            }}
            style={{
              display: 'block',
              width: '100%',
              textAlign: 'left',
              padding: '10px 12px',
              border: 'none',
              background: isCustom ? 'rgba(108,156,242,0.25)' : 'transparent',
              color: '#c5ccd8',
              cursor: 'pointer',
              fontSize: '0.88rem',
            }}
          >
            Otro (escribir…)
          </button>
        </div>
      )}
    </div>
  );
}

export default function AIGatewayTab({
  loading,
  isBusy,
  aiUsageStats,
  aiProviders,
  newProvider,
  setNewProvider,
  testPrompt,
  setTestPrompt,
  testResult,
  onRefresh,
  onCreateProvider,
  onUpdateProvider,
  onRunTest,
  embedded = false,
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [catalog, setCatalog] = useState([]);
  const [customModel, setCustomModel] = useState(false);
  const [draftModels, setDraftModels] = useState({});
  const [savingProviderId, setSavingProviderId] = useState(null);
  const [createPickerOpen, setCreatePickerOpen] = useState(false);
  const preset = PROVIDER_PRESETS[newProvider.provider_type] || PROVIDER_PRESETS.openai;
  const alreadyHasType = (aiProviders || []).some(
    (p) => (p.provider_type || '').toLowerCase() === newProvider.provider_type
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await api('/ai/models?capability=chat');
        if (!cancelled && Array.isArray(rows)) setCatalog(rows);
      } catch {
        /* usar fallbacks */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const modelOptions = useMemo(() => {
    const type = newProvider.provider_type || 'openai';
    const fallback = MODEL_FALLBACKS[type] || MODEL_FALLBACKS.openai;
    const fromApi = (catalog || []).filter(
      (m) => (m.provider_type || '').toLowerCase() === type && (m.capability || 'chat') === 'chat'
    );
    const byKey = new Map();
    for (const m of fallback) {
      byKey.set(m.model_key, { model_key: m.model_key, display_name: m.display_name });
    }
    for (const m of fromApi) {
      byKey.set(m.model_key, {
        model_key: m.model_key,
        display_name: m.display_name || m.model_key,
      });
    }
    return Array.from(byKey.values());
  }, [catalog, newProvider.provider_type]);

  const selectValue = useMemo(() => {
    if (customModel) return CUSTOM_MODEL;
    const keys = modelOptions.map((m) => m.model_key);
    if (keys.includes(newProvider.model_name)) return newProvider.model_name;
    return CUSTOM_MODEL;
  }, [customModel, modelOptions, newProvider.model_name]);

  useEffect(() => {
    const keys = modelOptions.map((m) => m.model_key);
    if (newProvider.model_name && !keys.includes(newProvider.model_name)) {
      setCustomModel(true);
    } else {
      setCustomModel(false);
    }
    // Solo al cambiar proveedor / catálogo
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newProvider.provider_type, modelOptions]);

  const selectPreset = (type) => {
    const p = PROVIDER_PRESETS[type];
    if (!p) return;
    setCustomModel(false);
    setCreatePickerOpen(false);
    setNewProvider({
      ...newProvider,
      provider_type: type,
      name: p.name,
      model_name: p.model_name,
      base_url: p.base_url,
      priority: p.priority,
      api_key: type === 'ollama' ? '' : newProvider.api_key,
    });
  };

  const onModelSelect = (value) => {
    if (value === CUSTOM_MODEL) {
      setCustomModel(true);
      return;
    }
    setCustomModel(false);
    const opt = modelOptions.find((m) => m.model_key === value);
    setNewProvider({
      ...newProvider,
      model_name: value,
      name: opt ? `${preset.label} · ${opt.display_name}` : newProvider.name,
    });
  };

  const optionsForType = (type) => {
    const t = (type || 'openai').toLowerCase();
    const fallback = MODEL_FALLBACKS[t] || MODEL_FALLBACKS.openai;
    const fromApi = (catalog || []).filter(
      (m) => (m.provider_type || '').toLowerCase() === t && (m.capability || 'chat') === 'chat'
    );
    const byKey = new Map();
    for (const m of fallback) {
      byKey.set(m.model_key, { model_key: m.model_key, display_name: m.display_name });
    }
    for (const m of fromApi) {
      byKey.set(m.model_key, {
        model_key: m.model_key,
        display_name: m.display_name || m.model_key,
      });
    }
    return Array.from(byKey.values());
  };

  const saveProviderModel = async (provider) => {
    const nextModel = draftModels[provider.id] ?? provider.model_name;
    if (!nextModel || nextModel === provider.model_name) return;
    if (!onUpdateProvider) return;
    setSavingProviderId(provider.id);
    try {
      await onUpdateProvider(provider.id, { model_name: nextModel });
      setDraftModels((prev) => {
        const copy = { ...prev };
        delete copy[provider.id];
        delete copy[`${provider.id}__custom`];
        delete copy[`${provider.id}__open`];
        return copy;
      });
    } finally {
      setSavingProviderId(null);
    }
  };

  const body = (
    <>
      {!embedded && (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>AI Gateway & Métricas de Consumo (Fase 5)</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Capa agnóstica de IA con fallback automático (Ollama ➔ OpenAI ➔ Anthropic) y registro de latencia/costos.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={16} /> Actualizar Métricas
        </button>
      </div>
      )}
      {embedded && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
          <button className="btn btn-secondary" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={16} /> Actualizar métricas
          </button>
        </div>
      )}

      {aiUsageStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px', marginBottom: '28px' }}>
          <div className="glass-card" style={{ padding: '18px', textAlign: 'center' }}>
            <Zap size={24} style={{ color: 'var(--accent-cyan)', margin: '0 auto 8px auto' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PETICIONES TOTALES</span>
            <p style={{ fontSize: '1.5rem', fontWeight: 800, margin: '4px 0' }}>{aiUsageStats.summary?.total_requests ?? 0}</p>
          </div>
          <div className="glass-card" style={{ padding: '18px', textAlign: 'center' }}>
            <Cpu size={24} style={{ color: '#10B981', margin: '0 auto 8px auto' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>% LOCAL VS PAGO</span>
            <p style={{ fontSize: '1.5rem', fontWeight: 800, margin: '4px 0', color: '#10B981' }}>{aiUsageStats.summary?.local_pct ?? 0}%</p>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              local {aiUsageStats.summary?.local_requests ?? 0} / pago {aiUsageStats.summary?.paid_requests ?? 0}
            </p>
          </div>
          <div className="glass-card" style={{ padding: '18px', textAlign: 'center' }}>
            <AlertTriangle size={24} style={{ color: 'var(--accent-purple)', margin: '0 auto 8px auto' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>FALLIDOS</span>
            <p style={{ fontSize: '1.5rem', fontWeight: 800, margin: '4px 0', color: 'var(--accent-purple)' }}>{aiUsageStats.summary?.failed_requests ?? 0}</p>
          </div>
          <div className="glass-card" style={{ padding: '18px', textAlign: 'center' }}>
            <DollarSign size={24} style={{ color: '#10B981', margin: '0 auto 8px auto' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>COSTO EST. (USD)</span>
            <p style={{ fontSize: '1.5rem', fontWeight: 800, margin: '4px 0', color: '#10B981' }}>${aiUsageStats.summary?.total_cost_usd ?? '0.0000'}</p>
          </div>
        </div>
      )}

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '8px' }}>Conectar proveedor</h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '12px' }}>
        Elige proveedor, modelo y API key. La URL se configura sola.
      </p>
      <div className="glass-card" style={{ padding: '20px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
          {Object.entries(PROVIDER_PRESETS).map(([type, p]) => {
            const active = newProvider.provider_type === type;
            const connected = (aiProviders || []).some(
              (x) => (x.provider_type || '').toLowerCase() === type
            );
            return (
              <button
                key={type}
                type="button"
                className={active ? 'btn btn-primary' : 'btn btn-secondary'}
                onClick={() => selectPreset(type)}
                style={{ minWidth: 120 }}
              >
                {p.label}
                {connected ? ' · ok' : ''}
              </button>
            );
          })}
        </div>

        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
          {preset.hint}
          {alreadyHasType ? ' · Ya tienes uno de este tipo; puedes agregar otro modelo o actualizar la key.' : ''}
        </p>

        <div style={{ marginBottom: '12px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
            Modelo
          </span>
          <ModelListPicker
            options={modelOptions}
            value={customModel ? '' : newProvider.model_name}
            isCustom={customModel || selectValue === CUSTOM_MODEL}
            open={createPickerOpen}
            setOpen={setCreatePickerOpen}
            label="Elegir modelo de IA"
            onChange={onModelSelect}
          />
          {(customModel || selectValue === CUSTOM_MODEL) && (
            <input
              placeholder="ej. gpt-4.1-mini / claude-opus-4 / mi-modelo:tag"
              value={newProvider.model_name}
              onChange={(e) => setNewProvider({ ...newProvider, model_name: e.target.value })}
              style={{ ...fieldStyle, marginTop: 8 }}
            />
          )}
        </div>

        {preset.needsKey ? (
          <label style={{ display: 'block', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <KeyRound size={14} /> API key
            </span>
            <input
              placeholder={`API key de ${preset.label}`}
              type="password"
              autoComplete="off"
              value={newProvider.api_key}
              onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
              style={fieldStyle}
            />
          </label>
        ) : (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Base URL: {preset.base_url}
          </p>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center' }}>
          <button className="btn btn-primary" type="button" onClick={onCreateProvider}>
            {preset.needsKey ? 'Guardar con API key' : 'Activar Ollama local'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setShowAdvanced((v) => !v)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Avanzado
          </button>
        </div>

        {showAdvanced && (
          <div
            style={{
              marginTop: '16px',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '12px',
              paddingTop: '14px',
              borderTop: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <input
              placeholder="Nombre visible"
              value={newProvider.name}
              onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
              style={fieldStyle}
            />
            <input
              placeholder="Base URL"
              value={newProvider.base_url}
              onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
              style={fieldStyle}
            />
            <input
              placeholder="Presupuesto mensual USD"
              value={newProvider.monthly_budget_usd}
              onChange={(e) => setNewProvider({ ...newProvider, monthly_budget_usd: e.target.value })}
              style={fieldStyle}
            />
            <input
              placeholder="Prioridad (menor = primero)"
              type="number"
              value={newProvider.priority}
              onChange={(e) => setNewProvider({ ...newProvider, priority: e.target.value })}
              style={fieldStyle}
            />
          </div>
        )}
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Cpu size={20} style={{ color: 'var(--accent-cyan)' }} /> Proveedores de IA Registrados y Cadena de Fallback
      </h3>

      <div className="grid-cards" style={{ marginBottom: '28px', overflow: 'visible' }}>
        {aiProviders.map((p) => {
          const opts = optionsForType(p.provider_type);
          const selected = draftModels[p.id] ?? p.model_name;
          const dirty = selected !== p.model_name;
          const isCustom = draftModels[`${p.id}__custom`] === true;
          const isOpen = draftModels[`${p.id}__open`] === true;
          return (
            <div key={p.id} className="glass-card" style={{ padding: '20px', overflow: 'visible' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span className="score-tag">PRIORIDAD #{p.priority}</span>
                <span className={`status-badge ${p.is_active ? 'status-verified' : 'status-pending'}`}>
                  {p.is_active ? (p.is_local ? 'LOCAL (GRATIS)' : 'CLOUD (API)') : 'INACTIVO'}
                </span>
              </div>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '6px 0' }}>{p.name}</h4>
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Cambiar a modelo actualizado
                </span>
                <ModelListPicker
                  options={opts}
                  value={isCustom ? '' : selected}
                  isCustom={isCustom}
                  open={isOpen}
                  setOpen={(open) =>
                    setDraftModels((prev) => ({ ...prev, [`${p.id}__open`]: open }))
                  }
                  label={`Cambiar modelo de ${p.name}`}
                  onChange={(v) => {
                    if (v === CUSTOM_MODEL) {
                      setDraftModels((prev) => ({
                        ...prev,
                        [`${p.id}__custom`]: true,
                        [p.id]: prev[p.id] ?? p.model_name,
                        [`${p.id}__open`]: false,
                      }));
                      return;
                    }
                    setDraftModels((prev) => ({
                      ...prev,
                      [`${p.id}__custom`]: false,
                      [p.id]: v,
                      [`${p.id}__open`]: false,
                    }));
                  }}
                />
                {isCustom && (
                  <input
                    value={selected}
                    onChange={(e) => setDraftModels((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    placeholder="modelo personalizado"
                    style={{ ...fieldStyle, marginTop: 8 }}
                  />
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 10 }}>
                En uso: <strong>{p.model_name}</strong>
                {dirty ? ` → ${selected}` : ''}
              </p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 12 }}>Base URL: {p.base_url}</p>
              <button
                type="button"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={!dirty || savingProviderId === p.id || !onUpdateProvider}
                onClick={() => saveProviderModel(p)}
              >
                {savingProviderId === p.id ? 'Guardando…' : dirty ? 'Actualizar modelo' : 'Sin cambios'}
              </button>
            </div>
          );
        })}
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Sparkles size={20} style={{ color: 'var(--accent-purple)' }} /> Probador Interactivo del AI Gateway
      </h3>

      <div className="glass-card" style={{ padding: '20px', marginBottom: '28px' }}>
        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Prompt de Prueba:</label>
          <textarea
            value={testPrompt}
            onChange={(e) => setTestPrompt(e.target.value)}
            rows={3}
            style={{ width: '100%', padding: '12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: '#FFF', border: '1px solid rgba(255,255,255,0.15)', fontSize: '0.9rem' }}
          />
        </div>
        <button className="btn btn-primary" onClick={onRunTest} disabled={loading || isBusy('ai-test')}>
          <Send size={16} /> {isBusy('ai-test') ? 'Probando…' : 'Ejecutar vía Gateway'}
        </button>
        {testResult && (
          <div style={{ marginTop: '20px', background: 'rgba(0,0,0,0.4)', padding: '18px', borderRadius: '10px', borderLeft: '4px solid var(--accent-cyan)' }}>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', fontSize: '0.85rem', flexWrap: 'wrap' }}>
              <span><strong>Proveedor Usado:</strong> {testResult.provider} ({testResult.model})</span>
              <span><strong>Fallback:</strong> {testResult.fallback_triggered ? 'Sí (conmutado)' : 'No (primario)'}</span>
              <span><strong>Tokens:</strong> {testResult.total_tokens}</span>
              <span><strong>Latencia:</strong> {testResult.latency_ms} ms</span>
              <span><strong>Costo:</strong> ${testResult.estimated_cost_usd} USD</span>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-sans)', fontSize: '0.92rem', lineHeight: 1.6 }}>{testResult.text}</pre>
          </div>
        )}
      </div>
    </>
  );

  if (embedded) return body;
  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      {body}
    </section>
  );
}
