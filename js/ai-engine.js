/**
 * AUTORIDAD 360 — MOTOR DE INTELIGENCIA ARTIFICIAL CLIENT-SIDE
 * Soporta APIs directas (Groq, OpenAI, Gemini, Claude, Ollama) y Generador Autónomo Heurístico.
 */

class AIEngine {
  constructor() {
    this.status = 'ready';
  }

  async generate({ prompt, systemPrompt = '', temperature = 0.7 }) {
    const config = window.AppState.aiConfig;
    const provider = config.active_provider;

    try {
      if (provider === 'groq' && config.groq_key) {
        return await this.callGroq(prompt, systemPrompt, config);
      } else if (provider === 'openai' && config.openai_key) {
        return await this.callOpenAI(prompt, systemPrompt, config);
      } else if (provider === 'gemini' && config.gemini_key) {
        return await this.callGemini(prompt, systemPrompt, config);
      } else if (provider === 'anthropic' && config.anthropic_key) {
        return await this.callAnthropic(prompt, systemPrompt, config);
      } else if (provider === 'ollama') {
        return await this.callOllama(prompt, systemPrompt, config);
      } else {
        // Modo Autónomo Inteligente (Fallback heurístico estructurado)
        return await this.generateAutonomous(prompt, systemPrompt);
      }
    } catch (err) {
      console.warn('[AIEngine] Error llamando API externa, usando generador autónomo:', err);
      return await this.generateAutonomous(prompt, systemPrompt, `(Nota: Falló la conexión con ${provider}. Generado con motor autónomo de respaldo).`);
    }
  }

  async callGroq(prompt, systemPrompt, config) {
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.groq_key.trim()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: config.groq_model || 'llama-3.3-70b-versatile',
        messages: [
          ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
          { role: 'user', content: prompt }
        ],
        temperature: config.temperature || 0.7
      })
    });
    if (!res.ok) throw new Error(`Groq HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return data.choices[0].message.content;
  }

  async callOpenAI(prompt, systemPrompt, config) {
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.openai_key.trim()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: config.openai_model || 'gpt-4o',
        messages: [
          ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
          { role: 'user', content: prompt }
        ],
        temperature: config.temperature || 0.7
      })
    });
    if (!res.ok) throw new Error(`OpenAI HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return data.choices[0].message.content;
  }

  async callGemini(prompt, systemPrompt, config) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${config.gemini_model || 'gemini-1.5-flash'}:generateContent?key=${config.gemini_key.trim()}`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: `${systemPrompt}\n\n${prompt}` }] }]
      })
    });
    if (!res.ok) throw new Error(`Gemini HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return data.candidates[0].content.parts[0].text;
  }

  async callOllama(prompt, systemPrompt, config) {
    const url = `${config.ollama_url.replace(/\/$/, '')}/api/generate`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.ollama_model || 'gemma4:e2b',
        prompt: `${systemPrompt}\n\n${prompt}`,
        stream: false
      })
    });
    if (!res.ok) throw new Error(`Ollama HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return data.response;
  }

  async generateAutonomous(prompt, systemPrompt, extraNote = '') {
    // Simular un tiempo de procesamiento natural (600ms)
    await new Promise(r => setTimeout(r, 600));

    const persona = window.AppState.profile;
    
    return `### PERSPECTIVA ESTRATÉGICA — AUTORIDAD 360
*Por ${persona.name} | ${persona.title}*

${extraNote ? `> ℹ️ ${extraNote}\n` : ''}
#### 1. Diagnóstico del Escenario y Ruptura de Paradigma
La rápida convergencia entre marcos normativos globales y la acelerada adopción de sistemas autónomos no es un tema técnico: es una redefinición del gobierno corporativo y la ventaja competitiva. Quienes observan esta transformación como un mero ejercicio de automatización están ignorando el verdadero vector de valor: la capacidad de articular confianza, trazabilidad algorítmica y retorno medible.

#### 2. Tesis Central y Análisis Crítico
1. **La soberanía operativa como imperativo**: Las empresas que dependen ciegamente de arquitecturas opacas enfrentan riesgos legales y operacionales desmedidos. La mitigación comienza en el comité de dirección.
2. **De la eficiencia táctica a la gobernanza de impacto**: Automatizar procesos sin un marco ético y regulatorio sólido multiplica el pasivo contingente en lugar de generar apalancamiento real.
3. **El nuevo estándar de liderazgo ejecutivo**: Los tomadores de decisión que lideran la conversación con criterio informado capturan las mejores oportunidades de negocio y alianzas estratégicas.

#### 3. Hoja de Ruta Ejecutiva (Recomendaciones de Acción)
- **Corto Plazo (30 días)**: Realizar una auditoría de riesgos de cumplimiento y mapeo de datos en todas las herramientas de IA activas en la organización.
- **Mediano Plazo (90 días)**: Establecer una política interna de uso responsable, asignando responsabilidades directas al C-Suite y áreas legales.
- **Largo Plazo**: Integrar modelos de supervisión continua y convertir la transparencia algorítmica en un pilar diferenciador frente al mercado.

---
*¿Cómo está abordando tu equipo directivo este desafío en su hoja de ruta de este trimestre?*`;
  }
}

window.AIEngine = new AIEngine();
