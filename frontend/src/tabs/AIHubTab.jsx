import React, { useState } from 'react';
import { Bot, Cpu } from 'lucide-react';
import AIGatewayTab from './AIGatewayTab';
import AgentsTab from './AgentsTab';

/**
 * Un solo lugar para modelos (API/Ollama) y agentes editoriales.
 */
export default function AIHubTab({
  loading,
  isBusy,
  aiUsageStats,
  aiProviders,
  aiStatsError,
  newProvider,
  setNewProvider,
  testPrompt,
  setTestPrompt,
  testResult,
  onRefreshModels,
  onCreateProvider,
  onUpdateProvider,
  onRemoveProvider,
  onRunTest,
  agentsCatalog,
  agentArticleId,
  setAgentArticleId,
  agentLimit,
  setAgentLimit,
  agentPipelineMode,
  setAgentPipelineMode,
  agentReason,
  setAgentReason,
  agentRunResult,
  agentBoard,
  onRefreshAgents,
  onRunPipeline,
  onRunNamed,
  onRunAutoCycle,
  initialSub = 'modelos',
}) {
  const [sub, setSub] = useState(initialSub === 'agentes' ? 'agentes' : 'modelos');

  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 6 }}>
          Inteligencia Artificial
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Configura proveedores (local u API) y corre agentes editoriales desde el mismo sitio.
        </p>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '20px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          paddingBottom: '10px',
          flexWrap: 'wrap',
        }}
      >
        <button
          type="button"
          className={`btn ${sub === 'modelos' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setSub('modelos')}
        >
          <Cpu size={16} /> Modelos y API
        </button>
        <button
          type="button"
          className={`btn ${sub === 'agentes' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => {
            setSub('agentes');
            onRefreshAgents?.();
          }}
        >
          <Bot size={16} /> Agentes
        </button>
      </div>

      {sub === 'modelos' ? (
        <AIGatewayTab
          embedded
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
          onRefresh={onRefreshModels}
          onCreateProvider={onCreateProvider}
          onUpdateProvider={onUpdateProvider}
          onRemoveProvider={onRemoveProvider}
          onRunTest={onRunTest}
        />
      ) : (
        <AgentsTab
          embedded
          isBusy={isBusy}
          agentsCatalog={agentsCatalog}
          agentBoard={agentBoard}
          agentArticleId={agentArticleId}
          setAgentArticleId={setAgentArticleId}
          agentLimit={agentLimit}
          setAgentLimit={setAgentLimit}
          agentPipelineMode={agentPipelineMode}
          setAgentPipelineMode={setAgentPipelineMode}
          agentReason={agentReason}
          setAgentReason={setAgentReason}
          agentRunResult={agentRunResult}
          onRefresh={onRefreshAgents}
          onRunPipeline={onRunPipeline}
          onRunNamed={onRunNamed}
          onRunAutoCycle={onRunAutoCycle}
        />
      )}
    </section>
  );
}
