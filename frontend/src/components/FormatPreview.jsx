import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const MEDIA_ORIGIN = (
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8012/api/v1'
).replace(/\/api\/v1\/?$/, '');

export function resolveMediaUrl(url) {
  if (!url) return null;
  if (/^https?:\/\//i.test(url) || url.startsWith('data:')) return url;
  if (url.startsWith('/')) return `${MEDIA_ORIGIN}${url}`;
  return `${MEDIA_ORIGIN}/${url}`;
}

/**
 * Vista previa de formatos. Si hay image_url en slides/covers, muestra la creatividad generada.
 */
export default function FormatPreview({
  format = 'linkedin',
  text = '',
  slides = [],
  coverUrl = null,
  authorName = 'Juan Vásquez',
  authorTitle = 'Abogado · Legal Tech & IA',
}) {
  const [slideIdx, setSlideIdx] = useState(0);

  const linkedinBody = useMemo(() => String(text || '').trim(), [text]);
  const safeSlides = Array.isArray(slides) ? slides : [];
  const current = safeSlides[slideIdx] || safeSlides[0];
  const currentImg = resolveMediaUrl(current?.image_url);
  const cover = resolveMediaUrl(coverUrl);

  if (format === 'linkedin') {
    return (
      <div style={frameStyle}>
        <div style={labelStyle}>Vista previa · LinkedIn</div>
        <div style={liCard}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            <div style={avatar}>{initials(authorName)}</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.92rem', color: '#111' }}>{authorName}</div>
              <div style={{ fontSize: '0.72rem', color: '#666' }}>{authorTitle}</div>
              <div style={{ fontSize: '0.7rem', color: '#888' }}>Ahora · Público</div>
            </div>
          </div>
          <div style={{ fontSize: '0.88rem', color: '#1a1a1a', lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
            {linkedinBody || 'El post aparecerá aquí…'}
          </div>
          {cover && (
            <img
              src={cover}
              alt="Creatividad"
              style={{ width: '100%', borderRadius: 8, marginTop: 12, display: 'block' }}
            />
          )}
          <div style={liActions}>
            <span>Recomendar</span>
            <span>Comentar</span>
            <span>Compartir</span>
          </div>
        </div>
      </div>
    );
  }

  if (format === 'carousel') {
    return (
      <div style={frameStyle}>
        <div style={labelStyle}>Vista previa · Carrusel</div>
        <div
          style={{
            ...carouselPhone,
            padding: currentImg ? 0 : 20,
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          {currentImg ? (
            <>
              <img
                src={currentImg}
                alt={current?.title || `Slide ${slideIdx + 1}`}
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              />
              <div
                style={{
                  position: 'absolute',
                  left: 10,
                  right: 10,
                  bottom: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 800,
                    color: '#fff',
                    background: 'rgba(0,0,0,0.55)',
                    padding: '4px 8px',
                    borderRadius: 6,
                  }}
                >
                  {slideIdx + 1} / {safeSlides.length || 1}
                </span>
                {safeSlides.length > 1 && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: '4px 8px' }}
                      disabled={slideIdx <= 0}
                      onClick={() => setSlideIdx((i) => Math.max(0, i - 1))}
                    >
                      <ChevronLeft size={14} />
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: '4px 8px' }}
                      disabled={slideIdx >= safeSlides.length - 1}
                      onClick={() => setSlideIdx((i) => Math.min(safeSlides.length - 1, i + 1))}
                    >
                      <ChevronRight size={14} />
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : current ? (
            <>
              <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontWeight: 800, marginBottom: 8 }}>
                {slideIdx + 1} / {safeSlides.length || 1}
              </div>
              <h4 style={{ margin: '0 0 10px', fontSize: '1.05rem', fontWeight: 800, color: '#fff' }}>
                {current.title || `Slide ${slideIdx + 1}`}
              </h4>
              <p style={{ margin: 0, fontSize: '0.88rem', color: 'rgba(255,255,255,0.85)', lineHeight: 1.5 }}>
                {current.content || current.text || '—'}
              </p>
              <p style={{ marginTop: 'auto', paddingTop: 12, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Usa “Generar imágenes” para creatividades de publicidad.
              </p>
              {safeSlides.length > 1 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px' }}
                    disabled={slideIdx <= 0}
                    onClick={() => setSlideIdx((i) => Math.max(0, i - 1))}
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px' }}
                    disabled={slideIdx >= safeSlides.length - 1}
                    onClick={() => setSlideIdx((i) => Math.min(safeSlides.length - 1, i + 1))}
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </>
          ) : (
            <p style={{ color: 'var(--text-secondary)', padding: 20 }}>Sin slides aún</p>
          )}
        </div>
      </div>
    );
  }

  if (format === 'newsletter') {
    return (
      <div style={frameStyle}>
        <div style={labelStyle}>Vista previa · Newsletter</div>
        <div style={mailCard}>
          <div style={{ borderBottom: '1px solid #e5e5e5', paddingBottom: 10, marginBottom: 12 }}>
            <div style={{ fontSize: '0.72rem', color: '#666' }}>De: {authorName}</div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: '#111', marginTop: 4 }}>
              Autoridad 360 — Edición
            </div>
          </div>
          {cover && (
            <img src={cover} alt="Portada" style={{ width: '100%', borderRadius: 6, marginBottom: 12 }} />
          )}
          <div style={{ fontSize: '0.88rem', color: '#222', lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
            {String(text || '').trim() || 'El cuerpo del newsletter aparecerá aquí…'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={frameStyle}>
      <div style={labelStyle}>Vista previa · Teleprompter</div>
      <div style={teleCard}>
        <div style={{ fontSize: '0.7rem', color: '#6ee7b7', marginBottom: 8, letterSpacing: '0.08em' }}>
          EN VIVO · GUION
        </div>
        {cover && (
          <img src={cover} alt="Cover" style={{ width: '100%', borderRadius: 8, marginBottom: 12 }} />
        )}
        <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.92rem', lineHeight: 1.7, color: '#ecfdf5', whiteSpace: 'pre-wrap' }}>
          {String(text || '').trim() || 'El guion aparecerá aquí…'}
        </div>
      </div>
    </div>
  );
}

function initials(name) {
  return String(name || 'JV')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || '')
    .join('') || 'JV';
}

const frameStyle = {
  background: 'rgba(0,0,0,0.25)',
  borderRadius: 12,
  padding: 14,
  border: '1px solid rgba(255,255,255,0.1)',
  height: '100%',
  minHeight: 280,
};

const labelStyle = {
  fontSize: '0.72rem',
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  marginBottom: 10,
  fontWeight: 700,
};

const liCard = {
  background: '#fff',
  borderRadius: 10,
  padding: 16,
  boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
};

const liActions = {
  display: 'flex',
  gap: 16,
  marginTop: 14,
  paddingTop: 12,
  borderTop: '1px solid #eee',
  fontSize: '0.75rem',
  color: '#555',
  fontWeight: 600,
};

const avatar = {
  width: 44,
  height: 44,
  borderRadius: '50%',
  background: 'linear-gradient(135deg, #0a66c2, #004182)',
  color: '#fff',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 800,
  fontSize: '0.85rem',
  flexShrink: 0,
};

const carouselPhone = {
  aspectRatio: '4 / 5',
  maxWidth: 280,
  margin: '0 auto',
  background: 'linear-gradient(160deg, #0f172a, #1e293b)',
  borderRadius: 16,
  padding: 20,
  border: '1px solid rgba(255,255,255,0.15)',
  display: 'flex',
  flexDirection: 'column',
};

const mailCard = {
  background: '#fafafa',
  borderRadius: 8,
  padding: 16,
  border: '1px solid #e8e8e8',
  maxHeight: 360,
  overflow: 'auto',
};

const teleCard = {
  background: '#022c22',
  borderRadius: 12,
  padding: 18,
  border: '1px solid rgba(16,185,129,0.35)',
  maxHeight: 360,
  overflow: 'auto',
};
