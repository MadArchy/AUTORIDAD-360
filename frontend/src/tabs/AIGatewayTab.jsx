import React from 'react';
import { RefreshCw, Zap, Cpu, AlertTriangle, DollarSign, Sparkles, Send } from 'lucide-react';

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
  onRunTest,
}) {
  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
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

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px' }}>Alta de proveedor (API key cifrada)</h3>
      <div className="glass-card" style={{ padding: '20px', marginBottom: '28px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <input placeholder="Nombre" value={newProvider.name} onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })} style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }} />
        <select value={newProvider.provider_type} onChange={(e) => setNewProvider({ ...newProvider, provider_type: e.target.value })} style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="gemini">Gemini</option>
          <option value="ollama">Ollama (local)</option>
        </select>
        <input placeholder="Modelo (gpt-4o / claude...)" value={newProvider.model_name} onChange={(e) => setNewProvider({ ...newProvider, model_name: e.target.value })} style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }} />
        <input placeholder="API key (no local)" type="password" value={newProvider.api_key} onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })} style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }} />
        <input placeholder="Base URL (opcional)" value={newProvider.base_url} onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })} style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }} />
        <input placeholder="Presupuesto mensual USD" value={newProvider.monthly_budget_usd} onChange={(e) => setNewProvider({ ...newProvider, monthly_budget_usd: e.target.value })} style={{ padding: '10px', borderRadius: 8, background: 'rgba(0,0,0,0.35)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }} />
        <button className="btn btn-primary" onClick={onCreateProvider}>Guardar proveedor</button>
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Cpu size={20} style={{ color: 'var(--accent-cyan)' }} /> Proveedores de IA Registrados y Cadena de Fallback
      </h3>

      <div className="grid-cards" style={{ marginBottom: '28px' }}>
        {aiProviders.map((p) => (
          <div key={p.id} className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span className="score-tag">PRIORIDAD #{p.priority}</span>
              <span className={`status-badge ${p.is_active ? 'status-verified' : 'status-pending'}`}>
                {p.is_active ? (p.is_local ? 'LOCAL (GRATIS)' : 'CLOUD (API)') : 'INACTIVO'}
              </span>
            </div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '6px 0' }}>{p.name}</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>Modelo: <strong>{p.model_name}</strong></p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Base URL: {p.base_url}</p>
          </div>
        ))}
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
    </section>
  );
}
