/**
 * AUTORIDAD 360 — ORQUESTADOR PRINCIPAL DE LA INTERFAZ WEB
 * Controla navegación, eventos de usuario, renderizado de vistas y estado dinámico.
 */

class AppUI {
  constructor() {
    this.currentTab = 'hoy';
    this.activeFormatTab = 'linkedin';
    this.currentPackage = null;
    this.currentSynthesis = null;
  }

  init() {
    this.bindEvents();
    this.renderHeaderProfile();
    this.renderAll();
    this.showToast('Bienvenido a Autoridad 360 (Modo Web Puro)', 'info');

    // Inicializar iconos de Lucide
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  bindEvents() {
    // Navegación por tabs en la barra lateral
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const tab = item.dataset.tab;
        if (tab) this.switchTab(tab);
      });
    });

    // Botón para refrescar noticias
    const btnRefreshNews = document.getElementById('btn-refresh-news');
    if (btnRefreshNews) {
      btnRefreshNews.addEventListener('click', async () => {
        btnRefreshNews.classList.add('loading');
        this.showToast('Buscando noticias en tiempo real...', 'info');
        await window.NewsService.fetchLiveNews();
        btnRefreshNews.classList.remove('loading');
        this.renderNewsTab();
        this.renderHoyTab();
        this.showToast('Inventario de noticias actualizado', 'success');
      });
    }

    // Buscador de noticias
    const newsSearch = document.getElementById('news-search-input');
    if (newsSearch) {
      newsSearch.addEventListener('input', (e) => {
        const query = e.target.value;
        const filterPillar = document.getElementById('news-pillar-filter')?.value || '';
        this.renderNewsList(filterPillar, query);
      });
    }

    // Filtro por pilar en noticias
    const pillarFilter = document.getElementById('news-pillar-filter');
    if (pillarFilter) {
      pillarFilter.addEventListener('change', (e) => {
        const query = document.getElementById('news-search-input')?.value || '';
        this.renderNewsList(e.target.value, query);
      });
    }

    // Botón generar síntesis desde noticias seleccionadas
    const btnGenerateSynthesis = document.getElementById('btn-generate-synthesis');
    if (btnGenerateSynthesis) {
      btnGenerateSynthesis.addEventListener('click', async () => {
        const selected = window.NewsService.getSelectedArticles();
        if (selected.length === 0) {
          this.showToast('Selecciona al menos 1 o 2 noticias para sintetizar', 'error');
          return;
        }
        this.switchTab('synthesis');
        this.populateSynthesisForm(selected);
      });
    }

    // Formulario de síntesis
    const formSynthesis = document.getElementById('form-synthesis');
    if (formSynthesis) {
      formSynthesis.addEventListener('submit', async (e) => {
        e.preventDefault();
        const selected = window.NewsService.getSelectedArticles();
        const customFocus = document.getElementById('synthesis-focus-input').value;
        const pillarSlug = document.getElementById('synthesis-pillar-select').value;

        const btnSubmit = formSynthesis.querySelector('button[type="submit"]');
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Generando ensayo ejecutivo...';
        if (window.lucide) window.lucide.createIcons();

        try {
          const result = await window.MultiNewsSynthesis.generateSynthesis({
            articles: selected.length > 0 ? selected : window.NewsService.articles.slice(0, 2),
            customFocus,
            pillarSlug
          });
          this.currentSynthesis = result;
          this.renderSynthesisResult(result);
          this.renderHoyTab();
          this.showToast('¡Ensayo de Autoridad generado con éxito!', 'success');
        } catch (err) {
          this.showToast(`Error: ${err.message}`, 'error');
        } finally {
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = '<i data-lucide="sparkles"></i> Generar Síntesis de Autoridad';
          if (window.lucide) window.lucide.createIcons();
        }
      });
    }

    // Formulario Multi-Formato
    const formFormat = document.getElementById('form-multiformat');
    if (formFormat) {
      formFormat.addEventListener('submit', async (e) => {
        e.preventDefault();
        const topic = document.getElementById('multiformat-topic-input').value;
        const language = document.getElementById('multiformat-lang-select').value;

        const btnSubmit = formFormat.querySelector('button[type="submit"]');
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Creando los 4 formatos...';
        if (window.lucide) window.lucide.createIcons();

        try {
          const pkg = await window.MultiFormatStudio.generateAllFormats({ topic, language });
          this.currentPackage = pkg;
          this.renderMultiFormatResults(pkg);
          this.renderHoyTab();
          this.showToast('Paquete Multi-Formato creado con éxito', 'success');
        } catch (err) {
          this.showToast(`Error: ${err.message}`, 'error');
        } finally {
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = '<i data-lucide="sparkles"></i> Generar Paquete de Contenido';
          if (window.lucide) window.lucide.createIcons();
        }
      });
    }

    // Pestañas internas de multi-formato (LinkedIn, Carrusel, Video, Newsletter)
    document.querySelectorAll('.format-subtab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const fmt = btn.dataset.format;
        document.querySelectorAll('.format-subtab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeFormatTab = fmt;
        this.switchFormatSubTab(fmt);
      });
    });

    // Guardar Configuración de IA
    const formAi = document.getElementById('form-ai-config');
    if (formAi) {
      formAi.addEventListener('submit', (e) => {
        e.preventDefault();
        const active_provider = document.getElementById('ai-provider-select').value;
        const groq_key = document.getElementById('ai-groq-key').value;
        const openai_key = document.getElementById('ai-openai-key').value;
        const gemini_key = document.getElementById('ai-gemini-key').value;
        const ollama_url = document.getElementById('ai-ollama-url').value;

        window.AppState.saveAiConfig({
          active_provider,
          groq_key,
          openai_key,
          gemini_key,
          ollama_url
        });

        this.showToast('Configuración de IA guardada en el navegador', 'success');
      });
    }

    // Guardar Perfil de Juan Vásquez
    const formProfile = document.getElementById('form-profile');
    if (formProfile) {
      formProfile.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('profile-name-input').value;
        const title = document.getElementById('profile-title-input').value;
        const bio = document.getElementById('profile-bio-input').value;

        window.AppState.saveProfile({ name, title, bio });
        this.renderHeaderProfile();
        this.showToast('Perfil de autoridad actualizado', 'success');
      });
    }
  }

  switchTab(tabId) {
    this.currentTab = tabId;

    // Actualizar menú lateral
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.tab === tabId);
    });

    // Actualizar vistas
    document.querySelectorAll('.tab-view').forEach(view => {
      view.classList.toggle('active', view.id === `tab-${tabId}`);
    });

    // Actualizar encabezado superior
    const titleMap = {
      hoy: 'Centro de Mando Editorial — Hoy',
      news: 'Radar de Noticias & Tendencias en Vivo',
      synthesis: 'Laboratorio de Síntesis Multi-Noticia',
      multiformat: 'Estudio de Producción Multi-Formato',
      calendar: 'Calendario Editorial & Cadencia',
      profile: 'Perfil de Autoridad & Pilares Estratégicos',
      aihub: 'Gateway de Inteligencia Artificial',
      metrics: 'Métricas de Autoridad, Leads & Conversión'
    };
    const headingEl = document.getElementById('topbar-page-heading');
    if (headingEl) headingEl.textContent = titleMap[tabId] || 'Autoridad 360';

    if (window.lucide) window.lucide.createIcons();
  }

  renderAll() {
    this.renderHoyTab();
    this.renderNewsTab();
    this.renderPillarsSelects();
    this.renderProfileTab();
    this.renderAiConfigTab();
    this.renderMetricsTab();
  }

  renderHeaderProfile() {
    const profile = window.AppState.profile;
    const nameEl = document.getElementById('sidebar-profile-name');
    const roleEl = document.getElementById('sidebar-profile-role');
    if (nameEl) nameEl.textContent = profile.name;
    if (roleEl) roleEl.textContent = profile.title.split(',')[0];
  }

  renderHoyTab() {
    const articles = window.NewsService.articles;
    const state = window.AppState;

    // KPIs
    const elKpiNews = document.getElementById('kpi-news-count');
    const elKpiPieces = document.getElementById('kpi-pieces-count');
    const elKpiLeads = document.getElementById('kpi-leads-count');

    if (elKpiNews) elKpiNews.textContent = articles.length;
    if (elKpiPieces) elKpiPieces.textContent = state.metrics.pieces_generated;
    if (elKpiLeads) elKpiLeads.textContent = state.metrics.leads_qualified;

    // Pilares cards
    const pillarsContainer = document.getElementById('hoy-pillars-container');
    if (pillarsContainer) {
      pillarsContainer.innerHTML = state.pillars.map(p => `
        <div class="card" style="border-left: 4px solid ${p.color};">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <span class="badge" style="background: ${p.color}22; color: ${p.color};">${p.target_pct}% Cuota</span>
            <span style="font-size: 0.75rem; color: var(--text-dim);">${p.current_count} piezas</span>
          </div>
          <h4 style="font-size: 0.95rem; margin-bottom: 4px;">${p.name}</h4>
          <p style="font-size: 0.78rem; color: var(--text-muted);">${p.description}</p>
        </div>
      `).join('');
    }

    // Lista de noticias recomendadas para hoy
    const recommendedList = document.getElementById('hoy-recommended-news');
    if (recommendedList) {
      recommendedList.innerHTML = articles.slice(0, 4).map(a => `
        <div class="article-item">
          <div class="article-header">
            <h4 class="article-title">${a.title}</h4>
            <span class="badge badge-primary">${a.score} Pts</span>
          </div>
          <p class="article-snippet">${a.snippet}</p>
          <div class="article-meta">
            <span><i data-lucide="building" style="width:12px;display:inline;"></i> ${a.source}</span>
            <span>•</span>
            <span class="badge badge-muted">${a.pillar_name}</span>
            <button class="btn btn-outline btn-sm" style="margin-left: auto;" onclick="window.AppUI.quickSynthesize(${a.id})">
              <i data-lucide="sparkles"></i> Sintetizar
            </button>
          </div>
        </div>
      `).join('');
    }
  }

  renderNewsTab() {
    this.renderNewsList();
  }

  renderNewsList(filterPillar = '', query = '') {
    const articles = window.NewsService.getArticles(filterPillar, query);
    const container = document.getElementById('news-articles-list');
    const countBadge = document.getElementById('selected-news-count');

    if (countBadge) {
      countBadge.textContent = window.NewsService.selectedArticleIds.size;
    }

    if (!container) return;

    if (articles.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 48px; color: var(--text-muted);">
          <i data-lucide="search-x" style="width: 48px; height: 48px; margin-bottom: 12px; stroke-width: 1.5;"></i>
          <p>No se encontraron noticias que coincidan con la búsqueda.</p>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    container.innerHTML = articles.map(a => {
      const isSelected = window.NewsService.selectedArticleIds.has(a.id);
      return `
        <div class="article-item ${isSelected ? 'selected' : ''}" id="article-${a.id}">
          <div class="article-header">
            <div style="display: flex; gap: 12px; align-items: flex-start;">
              <input type="checkbox" ${isSelected ? 'checked' : ''} style="margin-top: 4px; cursor: pointer;" onchange="window.AppUI.toggleArticleSelection(${a.id})">
              <div>
                <h4 class="article-title">${a.title}</h4>
                <div class="article-meta" style="margin-top: 4px;">
                  <span>${a.source}</span>
                  <span>•</span>
                  <span>${a.published_at}</span>
                  <span>•</span>
                  <span class="badge badge-muted">${a.pillar_name}</span>
                </div>
              </div>
            </div>
            <span class="badge badge-cyan">${a.score} Pts</span>
          </div>
          <p class="article-snippet" style="margin-left: 26px;">${a.snippet}</p>
          <div style="margin-left: 26px; display: flex; gap: 8px;">
            <a href="${a.url}" target="_blank" class="btn btn-outline btn-sm" style="text-decoration: none;">
              <i data-lucide="external-link" style="width: 12px;"></i> Fuente original
            </a>
            <button class="btn btn-secondary btn-sm" onclick="window.AppUI.quickFormatArticle(${a.id})">
              <i data-lucide="layers" style="width: 12px;"></i> Crear Formatos
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) window.lucide.createIcons();
  }

  toggleArticleSelection(id) {
    try {
      window.NewsService.toggleSelect(id);
      const itemEl = document.getElementById(`article-${id}`);
      if (itemEl) {
        itemEl.classList.toggle('selected', window.NewsService.selectedArticleIds.has(id));
      }
      const countBadge = document.getElementById('selected-news-count');
      if (countBadge) countBadge.textContent = window.NewsService.selectedArticleIds.size;
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  populateSynthesisForm(selectedArticles) {
    const focusInput = document.getElementById('synthesis-focus-input');
    const sourcesContainer = document.getElementById('synthesis-sources-list');

    if (focusInput) {
      focusInput.value = window.MultiNewsSynthesis.suggestFocus(selectedArticles);
    }

    if (sourcesContainer) {
      sourcesContainer.innerHTML = selectedArticles.map(a => `
        <div style="background: var(--bg-surface-raised); padding: 10px 14px; border-radius: var(--radius-md); font-size: 0.85rem; margin-bottom: 8px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 500;">${a.title}</span>
          <span class="badge badge-muted">${a.source}</span>
        </div>
      `).join('');
    }
  }

  renderSynthesisResult(result) {
    const container = document.getElementById('synthesis-result-container');
    if (!container) return;

    container.style.display = 'block';
    container.innerHTML = `
      <div class="card" style="margin-top: 24px; border-color: var(--primary);">
        <div class="card-header">
          <div>
            <span class="badge badge-primary" style="margin-bottom: 6px;">Ensayo de Autoridad C-Level</span>
            <h3 style="font-size: 1.25rem;">${result.focus}</h3>
            <p style="font-size: 0.8rem; color: var(--text-dim);">Pilar: ${result.pillar_name} | Por ${result.author}</p>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="window.ExportService.copyToClipboard(window.AppUI.currentSynthesis.content, 'Ensayo copiado')">
              <i data-lucide="copy" style="width: 14px;"></i> Copiar
            </button>
            <button class="btn btn-secondary btn-sm" onclick="window.ExportService.downloadFile(window.AppUI.currentSynthesis.content, 'Ensayo_Autoridad_${Date.now()}.md')">
              <i data-lucide="download" style="width: 14px;"></i> Markdown
            </button>
            <button class="btn btn-primary btn-sm" onclick="window.ExportService.printAsPdf(window.AppUI.currentSynthesis.focus, window.AppUI.currentSynthesis.content)">
              <i data-lucide="file-text" style="width: 14px;"></i> Exportar PDF
            </button>
          </div>
        </div>
        <div style="background: var(--bg-input); padding: 24px; border-radius: var(--radius-md); font-size: 0.9rem; line-height: 1.7; white-space: pre-wrap; font-family: var(--font-sans); color: var(--text-main); border: 1px solid var(--border-subtle);">
${result.content}
        </div>
      </div>
    `;

    if (window.lucide) window.lucide.createIcons();
  }

  renderMultiFormatResults(pkg) {
    const container = document.getElementById('multiformat-results-container');
    if (!container) return;

    container.style.display = 'block';

    // Rellenar LinkedIn
    const elLi = document.getElementById('fmt-linkedin-content');
    if (elLi) elLi.textContent = pkg.linkedin_post;

    // Rellenar Carrusel
    const elCarousel = document.getElementById('fmt-carousel-container');
    if (elCarousel && pkg.carousel_slides) {
      elCarousel.innerHTML = pkg.carousel_slides.map((s, idx) => `
        <div class="carousel-slide-card">
          <div>
            <div class="slide-number">SLIDE ${s.slide || idx + 1}</div>
            <h4 class="slide-headline">${s.title}</h4>
            <p class="slide-body">${s.content}</p>
          </div>
          <button class="btn btn-outline btn-sm" style="margin-top: 16px;" onclick="window.ExportService.copyToClipboard('${s.title}\\n\\n${s.content}', 'Slide copiada')">
            <i data-lucide="copy" style="width: 12px;"></i> Copiar Slide
          </button>
        </div>
      `).join('');
    }

    // Rellenar Video
    const elVideo = document.getElementById('fmt-video-content');
    if (elVideo) elVideo.textContent = pkg.video_script;

    // Rellenar Newsletter
    const elNews = document.getElementById('fmt-newsletter-content');
    if (elNews) elNews.textContent = pkg.newsletter_edition;

    if (window.lucide) window.lucide.createIcons();
  }

  switchFormatSubTab(fmt) {
    document.querySelectorAll('.format-panel').forEach(panel => {
      panel.style.display = panel.id === `fmt-panel-${fmt}` ? 'block' : 'none';
    });
  }

  quickSynthesize(articleId) {
    const article = window.NewsService.articles.find(a => a.id === articleId);
    if (!article) return;
    window.NewsService.clearSelection();
    window.NewsService.toggleSelect(articleId);
    this.switchTab('synthesis');
    this.populateSynthesisForm([article]);
  }

  quickFormatArticle(articleId) {
    const article = window.NewsService.articles.find(a => a.id === articleId);
    if (!article) return;
    this.switchTab('multiformat');
    const input = document.getElementById('multiformat-topic-input');
    if (input) input.value = article.title;
  }

  renderPillarsSelects() {
    const pillars = window.AppState.pillars;
    const selectSynth = document.getElementById('synthesis-pillar-select');
    const selectFilter = document.getElementById('news-pillar-filter');

    const optionsHtml = pillars.map(p => `<option value="${p.slug}">${p.name}</option>`).join('');

    if (selectSynth) selectSynth.innerHTML = optionsHtml;
    if (selectFilter) {
      selectFilter.innerHTML = '<option value="">Todos los pilares</option>' + optionsHtml;
    }
  }

  renderProfileTab() {
    const profile = window.AppState.profile;
    const elName = document.getElementById('profile-name-input');
    const elTitle = document.getElementById('profile-title-input');
    const elBio = document.getElementById('profile-bio-input');

    if (elName) elName.value = profile.name;
    if (elTitle) elTitle.value = profile.title;
    if (elBio) elBio.value = profile.bio;
  }

  renderAiConfigTab() {
    const config = window.AppState.aiConfig;
    const elProv = document.getElementById('ai-provider-select');
    const elGroq = document.getElementById('ai-groq-key');
    const elOpenAi = document.getElementById('ai-openai-key');
    const elGemini = document.getElementById('ai-gemini-key');
    const elOllama = document.getElementById('ai-ollama-url');

    if (elProv) elProv.value = config.active_provider;
    if (elGroq) elGroq.value = config.groq_key;
    if (elOpenAi) elOpenAi.value = config.openai_key;
    if (elGemini) elGemini.value = config.gemini_key;
    if (elOllama) elOllama.value = config.ollama_url;
  }

  renderMetricsTab() {
    const metrics = window.AppState.metrics;
    const elTotalArt = document.getElementById('metric-total-articles');
    const elPieces = document.getElementById('metric-total-pieces');
    const elLeads = document.getElementById('metric-total-leads');
    const elConv = document.getElementById('metric-conversion-rate');

    if (elTotalArt) elTotalArt.textContent = metrics.total_articles_analyzed;
    if (elPieces) elPieces.textContent = metrics.pieces_generated;
    if (elLeads) elLeads.textContent = metrics.leads_qualified;
    if (elConv) elConv.textContent = metrics.conversion_rate;
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const iconName = type === 'success' ? 'check-circle-2' : type === 'error' ? 'alert-triangle' : 'info';
    toast.innerHTML = `<i data-lucide="${iconName}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    if (window.lucide) window.lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.AppUI = new AppUI();
  window.AppUI.init();
});
