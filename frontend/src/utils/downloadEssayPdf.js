/** Genera y descarga un archivo PDF real del ensayo fusionado. */
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function slugifyFilename(title) {
  const base = String(title || 'ensayo-juan-vasquez')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 72);
  return `${base || 'ensayo-juan-vasquez'}.pdf`;
}

function buildRenderableHtml({ title, author, thesis, bodyHtml, sourcesCount }) {
  const safeTitle = escapeHtml(title || 'Ensayo editorial');
  const safeAuthor = escapeHtml(author || 'Juan Vásquez');
  const safeThesis = escapeHtml(thesis || '');
  const count = Number(sourcesCount) || 0;
  const body = bodyHtml || '<p>Sin contenido.</p>';

  return `
    <div class="pdf-root">
      <p class="pdf-brand">Autoridad 360 · Thought leadership</p>
      <h1 class="pdf-title">${safeTitle}</h1>
      <p class="pdf-byline">${safeAuthor}${count ? ` · ${count} fuentes acreditadas` : ''}</p>
      ${
        safeThesis
          ? `<div class="pdf-thesis"><strong>Tesis</strong><p>${safeThesis}</p></div>`
          : ''
      }
      <div class="pdf-body">${body}</div>
    </div>
  `;
}

const PDF_STYLES = `
  .pdf-root {
    width: 794px;
    padding: 48px 56px 64px;
    background: #ffffff;
    color: #111827;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 15px;
    line-height: 1.65;
    text-align: left;
  }
  .pdf-brand {
    margin: 0 0 12px;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
  }
  .pdf-title {
    margin: 0 0 10px;
    font-size: 28px;
    line-height: 1.25;
    font-weight: 700;
    color: #0f172a;
  }
  .pdf-byline {
    margin: 0 0 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e2e8f0;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 13px;
    color: #475569;
  }
  .pdf-thesis {
    margin: 0 0 24px;
    padding: 14px 16px;
    border-left: 3px solid #0ea5e9;
    background: #f8fafc;
    font-family: Arial, Helvetica, sans-serif;
  }
  .pdf-thesis strong {
    display: block;
    margin-bottom: 6px;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #64748b;
  }
  .pdf-thesis p { margin: 0; color: #1e293b; font-size: 14px; }
  .pdf-body .jv-essay { max-width: none; }
  .pdf-body .jv-lede {
    margin: 0 0 1.1em;
    font-size: 17px;
    font-weight: 650;
    line-height: 1.45;
    color: #0f172a;
  }
  .pdf-body h2, .pdf-body h3 {
    margin: 1.35em 0 0.45em;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 16px;
    color: #0f172a;
  }
  .pdf-body p { margin: 0 0 0.85em; }
  .pdf-body ul, .pdf-body ol { margin: 0 0 1em 1.25em; padding: 0; }
  .pdf-body li { margin: 0 0 0.35em; }
  .pdf-body a { color: #0369a1; }
  .pdf-body .jv-perspective {
    margin: 0.5em 0 1.1em;
    padding: 14px 16px;
    border-left: 3px solid #0284c7;
    background: #f0f9ff;
  }
  .pdf-body .jv-perspective p { margin: 0; }
  .pdf-body .jv-disclaimer {
    margin-top: 1.4em;
    padding-top: 0.9em;
    border-top: 1px solid #e2e8f0;
    font-size: 12px;
    color: #64748b;
    font-style: italic;
  }
  .pdf-body .jv-sources {
    margin-top: 1.6em;
    padding-top: 1em;
    border-top: 1px solid #cbd5e1;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 12.5px;
  }
  .pdf-body .jv-sources h2 {
    margin-top: 0;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
  }
  .pdf-body .jv-sources__note { color: #64748b; margin-bottom: 0.6em; }
`;

/**
 * Genera un PDF y lo descarga al equipo.
 * @returns {Promise<{ ok: boolean, filename: string, error?: string }>}
 */
export async function downloadEssayAsPdf({
  title,
  author = 'Juan Vásquez',
  thesis = '',
  bodyHtml = '',
  sourcesCount = 0,
} = {}) {
  if (!bodyHtml && !title) {
    return { ok: false, filename: '', error: 'No hay artículo para exportar.' };
  }

  const filename = slugifyFilename(title);
  const host = document.createElement('div');
  host.setAttribute('aria-hidden', 'true');
  host.style.cssText = [
    'position:fixed',
    'left:-12000px',
    'top:0',
    'width:794px',
    'background:#ffffff',
    'z-index:-1',
    'pointer-events:none',
  ].join(';');

  const style = document.createElement('style');
  style.textContent = PDF_STYLES;
  host.appendChild(style);

  const content = document.createElement('div');
  content.innerHTML = buildRenderableHtml({
    title,
    author,
    thesis,
    bodyHtml,
    sourcesCount,
  });
  host.appendChild(content);
  document.body.appendChild(host);

  try {
    const target = host.querySelector('.pdf-root');
    const canvas = await html2canvas(target, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      logging: false,
      windowWidth: 794,
    });

    if (!canvas.width || !canvas.height) {
      return { ok: false, filename, error: 'No se pudo renderizar el artículo para PDF.' };
    }

    const imgData = canvas.toDataURL('image/jpeg', 0.92);
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 0;
    const imgWidth = pageWidth - margin * 2;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = margin;

    pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight, undefined, 'FAST');
    heightLeft -= pageHeight;

    while (heightLeft > 1) {
      position -= pageHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight, undefined, 'FAST');
      heightLeft -= pageHeight;
    }

    pdf.save(filename);
    return { ok: true, filename };
  } catch (err) {
    return {
      ok: false,
      filename,
      error: err?.message || 'No se pudo generar el PDF.',
    };
  } finally {
    host.remove();
  }
}
