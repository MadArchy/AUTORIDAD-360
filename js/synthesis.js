/**
 * AUTORIDAD 360 — MÓDULO DE SÍNTESIS MULTI-NOTICIA
 * Cruza de 2 a 5 artículos de actualidad para construir ensayos y artículos de autoridad.
 */

class MultiNewsSynthesis {
  suggestFocus(articles) {
    if (!articles || articles.length === 0) return 'Impacto estratégico y gobernanza en la adopción de IA corporativa.';
    
    const titles = articles.map(a => a.title).join(' ');
    if (/ley|regulaci|reglamento|normativ|act/i.test(titles)) {
      return 'Convergencia regulatoria: Cómo blindar la operación corporativa ante la nueva legislación de IA.';
    }
    if (/agente|b2b|banco|costo|roi|financ/i.test(titles)) {
      return 'Rentabilidad y despliegue de agentes autónomos en modelos de negocio B2B de alta escala.';
    }
    if (/ceo|marca|autoridad|lider|confianza/i.test(titles)) {
      return 'El rol del liderazgo ejecutivo en la construcción de confianza y posicionamiento digital.';
    }
    return 'Transformación digital con IA: Del experimento aislado a la gobernanza y rentabilidad empresarial.';
  }

  async generateSynthesis({ articles, customFocus = '', pillarSlug = 'ia-negocio' }) {
    if (!articles || articles.length < 1) {
      throw new Error('Debes seleccionar al menos 1 o más noticias para sintetizar.');
    }

    const persona = window.AppState.profile;
    const focus = customFocus || this.suggestFocus(articles);
    const pillar = window.AppState.pillars.find(p => p.slug === pillarSlug) || window.AppState.pillars[0];

    const sourcesContext = articles.map((a, i) => `[Fuente ${i + 1}] "${a.title}" (${a.source}) -> ${a.snippet}`).join('\n\n');

    const systemPrompt = `Eres el director editorial y estratega de contenido de ${persona.name} (${persona.title}). Tu objetivo es producir un ensayo de liderazgo de pensamiento y alta autoridad ejecutiva. Tu tono es analítico, persuasivo, directo, sofisticado y orientado a negocios y gobernanza (C-Level).`;

    const userPrompt = `A partir de las siguientes fuentes de noticias de actualidad:
${sourcesContext}

ENFOQUE EDITORIAL SOLICITADO:
"${focus}"

PILAR TEMÁTICO: ${pillar.name}

Genera un ensayo analítico completo estructurado con:
1. TÍTULO ATRACTIVO Y DE ALTA AUTORIDAD (formato Markdown H1)
2. RESUMEN EJECUTIVO (TL;DR de 3 líneas para directivos)
3. TESIS CENTRAL (El argumento disruptivo que desafía el sentido común)
4. CUERPO ANALÍTICO (3 secciones profundas con subtítulos H3 que conecten los hechos de las fuentes con la estrategia de negocio)
5. RIESGOS Y CONTRA-ARGUMENTOS (Lo que la mayoría pasa por alto)
6. CONCLUSIÓN Y HOJA DE RUTA PRÁCTICA (3 pasos de acción directa)

Firma el documento como: ${persona.name} | ${persona.title}`;

    const content = await window.AIEngine.generate({
      prompt: userPrompt,
      systemPrompt,
      temperature: 0.7
    });

    const synthesisObj = {
      id: Date.now(),
      created_at: new Date().toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
      focus,
      pillar_name: pillar.name,
      pillar_slug: pillar.slug,
      sources_count: articles.length,
      sources: articles.map(a => ({ title: a.title, source: a.source, url: a.url })),
      content,
      author: persona.name
    };

    // Marcar artículos como trabajados en el estado
    articles.forEach(a => window.AppState.markArticleWorked(a.id));
    window.AppState.addSynthesis(synthesisObj);

    return synthesisObj;
  }
}

window.MultiNewsSynthesis = new MultiNewsSynthesis();
