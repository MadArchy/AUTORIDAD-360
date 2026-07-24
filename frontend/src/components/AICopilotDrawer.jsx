import React, { useState } from 'react';
import { Bot, Send, Sparkles, X, Check, RefreshCw } from 'lucide-react';
import { fetchApi } from '../api';

const QUICK_PROMPTS = [
  { label: '⚖️ Tono Legal/Técnico', prompt: 'Reescribe este contenido con un tono más jurídico, técnico y riguroso.' },
  { label: '🚀 Optimizar SEO', prompt: 'Mejora el texto para SEO, añadiendo palabras clave y subtítulos claros.' },
  { label: '📝 Hacer más conciso', prompt: 'Resume este contenido manteniendo los puntos clave pero eliminando redundancias.' },
  { label: '⚠️ Disclaimer Legal', prompt: 'Añade una cláusula o disclaimer de exención de responsabilidad profesional al final.' },
  { label: '📱 Hilo de Redes', prompt: 'Adapta este artículo en un formato de post estructurado para LinkedIn / X con ganchos.' },
];

export default function AICopilotDrawer({
  isOpen,
  onClose,
  targetItem,
  itemType = 'article', // 'article' | 'blog'
  onApplyRefinement,
}) {
  const [instruction, setInstruction] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen || !targetItem) return null;

  const handleSendPrompt = async (promptToSend) => {
    const textPrompt = promptToSend || instruction;
    if (!textPrompt.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const endpoint = itemType === 'blog' 
        ? `/blog/${targetItem.id}/copilot` 
        : `/articles/${targetItem.id}/copilot`;
      
      const data = await fetchApi(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          instruction: textPrompt,
          target_field: itemType === 'blog' ? 'content_html' : 'full_text',
        }),
      });

      setResult(data);
    } catch (err) {
      setError(err.message || 'Error al comunicarse con el Copiloto de IA.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApply = () => {
    if (result && result.refined_content) {
      onApplyRefinement?.(result.refined_content);
      onClose();
    }
  };

  return (
    <div className="copilot-drawer-overlay" style={overlayStyle}>
      <div className="copilot-drawer glass-panel" style={drawerStyle}>
        {/* Header */}
        <div style={headerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="icon-badge" style={{ background: 'linear-gradient(135deg, #6366f1, #a855f7)', padding: '8px', borderRadius: '8px' }}>
              <Sparkles size={20} color="#FFF" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#FFF' }}>Copiloto de IA</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Refinamiento interactivo para {itemType === 'blog' ? 'Post de Blog' : 'Noticia'}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="btn btn-secondary" style={{ padding: '6px 10px' }}>
            <X size={16} />
          </button>
        </div>

        {/* Context Preview */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 6px 0' }}>Enfoque de trabajo:</p>
          <h4 style={{ margin: 0, fontSize: '0.92rem', color: '#6366f1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {targetItem.title}
          </h4>
        </div>

        {/* Drawer Body / Conversation */}
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Quick Action Pills */}
          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
              Acciones rápidas sugeridas:
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {QUICK_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  className="pill-btn"
                  onClick={() => {
                    setInstruction(item.prompt);
                    handleSendPrompt(item.prompt);
                  }}
                  style={pillStyle}
                  disabled={isLoading}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div style={{ padding: '12px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', fontSize: '0.85rem' }}>
              {error}
            </div>
          )}

          {/* Result Box */}
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-secondary)' }}>
              <RefreshCw className="spin" size={28} style={{ marginBottom: '12px', color: '#a855f7' }} />
              <p style={{ margin: 0, fontSize: '0.9rem' }}>El Copiloto de IA está analizando e iterando el contenido…</p>
            </div>
          ) : result ? (
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '12px', padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.78rem', color: '#a855f7', fontWeight: 600 }}>
                  Modelo: {result.model_used}
                </span>
                <button className="btn btn-primary" onClick={handleApply} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                  <Check size={14} /> Aplicar Cambios
                </button>
              </div>
              <div style={{ fontSize: '0.88rem', color: '#e2e8f0', whiteSpace: 'pre-wrap', maxHeight: '280px', overflowY: 'auto', lineHeight: '1.5' }}>
                {result.refined_content}
              </div>
            </div>
          ) : (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', border: '1px dashed rgba(255,255,255,0.15)', borderRadius: '12px' }}>
              <Bot size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
              <p style={{ margin: 0, fontSize: '0.85rem' }}>Selecciona una acción rápida o escribe una instrucción abajo para interactuar con la IA.</p>
            </div>
          )}
        </div>

        {/* Drawer Footer Input */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255,255,255,0.08)', background: 'var(--bg-card)' }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendPrompt();
            }}
            style={{ display: 'flex', gap: '8px' }}
          >
            <input
              type="text"
              placeholder="Ej: Reescribe el párrafo 2 con más enfoque en IA…"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              disabled={isLoading}
              style={inputStyle}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading || !instruction.trim()}
              style={{ padding: '10px 16px' }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

const overlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.65)',
  backdropFilter: 'blur(4px)',
  zIndex: 1000,
  display: 'flex',
  justifyContent: 'flex-end',
};

const drawerStyle = {
  width: '100%',
  maxWidth: '480px',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  borderRadius: 0,
  borderLeft: '1px solid rgba(255, 255, 255, 0.15)',
  background: '#0b0f19',
};

const headerStyle = {
  padding: '16px 20px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
};

const pillStyle = {
  padding: '6px 12px',
  borderRadius: '20px',
  background: 'rgba(99, 102, 241, 0.12)',
  border: '1px solid rgba(99, 102, 241, 0.3)',
  color: '#c7d2fe',
  fontSize: '0.78rem',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
};

const inputStyle = {
  flex: 1,
  padding: '10px 14px',
  borderRadius: '8px',
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.15)',
  color: '#FFF',
  fontSize: '0.85rem',
};
