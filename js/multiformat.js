/**
 * AUTORIDAD 360 — MÓDULO MULTI-FORMATO
 * Genera piezas para LinkedIn, Carruseles, Guiones de Video y Newsletters.
 */

class MultiFormatStudio {
  async generateAllFormats({ topic, coreArticle = null, language = 'es' }) {
    const persona = window.AppState.profile;
    const context = coreArticle ? `Noticia base: "${coreArticle.title}" (${coreArticle.source})\nDetalle: ${coreArticle.snippet}` : '';

    const systemPrompt = `Eres el redactor jefe y estratega de distribución de ${persona.name}. Especialista en copywriting B2B de alto impacto para ejecutivos y fundadores.`;

    const prompt = `Tema central: "${topic}"
${context}

Genera un paquete de contenido multi-formato coordinado en idioma ${language === 'es' ? 'Español' : 'Inglés'}. Devuelve el contenido en formato JSON estrictamente válido con la siguiente estructura:
{
  "linkedin_post": "Texto completo del post de LinkedIn con gancho de 1 línea, espaciado legible, viñetas, llamado a la acción y 3 hashtags profesionales.",
  "carousel_slides": [
    { "slide": 1, "title": "PORTADA", "content": "Título llamativo + Subtítulo provocador" },
    { "slide": 2, "title": "EL PROBLEMA", "content": "Lo que la mayoría de empresas está haciendo mal" },
    { "slide": 3, "title": "EL INSIGHT", "content": "El dato o cambio de regla clave" },
    { "slide": 4, "title": "LA ESTRATEGIA", "content": "3 pasos prácticos para ejecutar hoy" },
    { "slide": 5, "title": "CONCLUSIÓN", "content": "Llamada a la acción y debate" }
  ],
  "video_script": "Guion estructurado para video corto (60 seg):\n[0:00-0:05] Gancho visual y verbal\n[0:05-0:20] El contexto del problema\n[0:20-0:45] Los 3 puntos clave de valor\n[0:45-1:00] Llamado a la acción para comentar o contactar.",
  "newsletter_edition": "ASUNTO: Asunto con alto open-rate\nPREVIEW: Texto de vista previa\n\nCUERPO:\nEstimado colega directivo...\n(Desarrollo de 3 párrafos de alta densidad y valor)..."
}`;

    const rawResponse = await window.AIEngine.generate({ prompt, systemPrompt });

    let parsed;
    try {
      // Intentar extraer JSON si viene envuelto en markdown ```json
      const jsonMatch = rawResponse.match(/```(?:json)?([\s\S]*?)```/) || [null, rawResponse];
      parsed = JSON.parse(jsonMatch[1].trim());
    } catch (e) {
      // Fallback si la respuesta no vino en JSON limpio
      parsed = {
        linkedin_post: `🚀 ${topic}\n\nLa mayoría de las empresas cometen un error crítico al abordar este escenario: confunden velocidad con estrategia.\n\nAquí los 3 principios clave que aplicamos con directores:\n\n1️⃣ Claridad en la gobernanza antes de la escala.\n2️⃣ Automatización con retorno financiero medible.\n3️⃣ Cultura de toma de decisiones informada.\n\n¿Cuál es la prioridad en tu organización este trimestre?\n\n#InteligenciaArtificial #Liderazgo #EstrategiaB2B`,
        carousel_slides: [
          { slide: 1, title: 'El Cambio Silencioso', content: topic },
          { slide: 2, title: 'El Error Común', content: 'Invertir en herramientas sin definir el marco de gobernanza corporativa.' },
          { slide: 3, title: 'La Oportunidad', content: 'Capturar ventaja competitiva mientras otros siguen en etapa de prueba.' },
          { slide: 4, title: 'Plan de Acción', content: '1. Auditoría interna\n2. Capacitación C-Level\n3. Despliegue seguro' },
          { slide: 5, title: '¿Siguiente Paso?', content: 'Guarda esta guía y compártela con tu equipo de liderazgo.' }
        ],
        video_script: `[0:00 - GANCHO]\nSi diriges una empresa en 2026, esto cambiará cómo operas en los próximos 90 días.\n\n[0:15 - PROBLEMA]\n${topic} está obligando a reescribir las reglas del juego corporativo.\n\n[0:40 - SOLUCIÓN]\nLa clave no es usar más tecnología, sino gobernarla con retorno real.\n\n[0:55 - CTA]\nSígueme para más análisis estratégicos sobre IA y negocios.`,
        newsletter_edition: `ASUNTO: Lo que ningún directivo te dice sobre ${topic}\n\nEstimado lector,\n\nEn los últimos días hemos visto un cambio de paradigma crucial. Quienes actúen ahora consolidarán su posición de liderazgo en el mercado...\n\nUn cordial saludo,\n${persona.name}`
      };
    }

    const pkg = {
      id: Date.now(),
      created_at: new Date().toLocaleDateString('es-MX'),
      topic,
      ...parsed
    };

    window.AppState.addPackage(pkg);
    return pkg;
  }
}

window.MultiFormatStudio = new MultiFormatStudio();
