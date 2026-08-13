/**
 * AUTORIDAD 360 — MÓDULO DE EXPORTACIÓN Y COPIADO
 * Permite copiar al portapapeles, descargar en Markdown/JSON y exportar a PDF.
 */

class ExportService {
  async copyToClipboard(text, successMsg = 'Copiado al portapapeles') {
    try {
      await navigator.clipboard.writeText(text);
      window.AppUI.showToast(successMsg, 'success');
    } catch (err) {
      // Fallback manual para navegadores antiguos
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      window.AppUI.showToast(successMsg, 'success');
    }
  }

  downloadFile(content, filename, type = 'text/markdown;charset=utf-8') {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    window.AppUI.showToast(`Archivo "${filename}" descargado con éxito`, 'success');
  }

  printAsPdf(title, markdownOrHtml) {
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Por favor permite las ventanas emergentes para generar el PDF.');
      return;
    }

    const persona = window.AppState.profile;
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>${title} — Autoridad 360</title>
        <style>
          body { font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1e293b; padding: 40px; max-width: 800px; margin: 0 auto; }
          .header { border-bottom: 2px solid #6366f1; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-end; }
          .logo { font-size: 20px; font-weight: 800; color: #6366f1; letter-spacing: -0.5px; }
          .author { font-size: 13px; color: #64748b; text-align: right; }
          h1 { font-size: 24px; color: #0f172a; margin-top: 0; line-height: 1.3; }
          h3, h4 { color: #334155; margin-top: 20px; }
          pre, code { background: #f1f5f9; padding: 10px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; word-break: break-word; }
          blockquote { border-left: 4px solid #6366f1; margin: 0; padding-left: 15px; color: #475569; font-style: italic; }
          .footer { margin-top: 40px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }
          @media print {
            body { padding: 0; }
            .no-print { display: none; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="logo">AUTORIDAD 360</div>
          <div class="author">${persona.name}<br>${persona.title}</div>
        </div>
        <div class="content">
          ${this.formatMarkdownToHtml(markdownOrHtml)}
        </div>
        <div class="footer">
          Documento Ejecutivo generado por Autoridad 360 | ${new Date().toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
        <script>
          window.onload = function() {
            setTimeout(function() { window.print(); }, 300);
          }
        </script>
      </body>
      </html>
    `);
    printWindow.document.close();
  }

  formatMarkdownToHtml(md) {
    if (!md) return '';
    return md
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/gim, '<p></p>')
      .replace(/\n/gim, '<br>');
  }
}

window.ExportService = new ExportService();
