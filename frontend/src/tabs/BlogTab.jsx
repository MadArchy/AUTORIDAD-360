import React from 'react';
import { ExternalLink } from 'lucide-react';

const PUBLIC_BLOG_URL =
  import.meta.env.VITE_PUBLIC_BLOG_URL || 'http://127.0.0.1:3002';
const PUBLIC_BLOG_POST_URL =
  import.meta.env.VITE_PUBLIC_BLOG_POST_URL ||
  `${PUBLIC_BLOG_URL.replace(/\/$/, '')}/blog/{slug}`;

function getPublicPostUrl(slug) {
  const encodedSlug = encodeURIComponent(slug);
  if (PUBLIC_BLOG_POST_URL.includes('{slug}')) {
    return PUBLIC_BLOG_POST_URL.replace('{slug}', encodedSlug);
  }
  const separator = PUBLIC_BLOG_POST_URL.includes('?') ? '&' : '?';
  return `${PUBLIC_BLOG_POST_URL}${separator}slug=${encodedSlug}`;
}

/** Admin: moderación de borradores. El sitio público es Next.js en :3002. */
export default function BlogTab({
  publishedBlogPosts,
  pendingBlogPosts,
  approvePendingBlog,
  publishPendingBlog,
}) {
  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px' }}>
            Blog editorial (admin)
          </h2>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            Aprueba y publica aquí. El público lee en Next.js — no mezclar stacks.
          </p>
        </div>
        <a
          className="btn btn-primary"
          href={PUBLIC_BLOG_URL}
          target="_blank"
          rel="noopener noreferrer"
          style={{ textDecoration: 'none', alignSelf: 'flex-start' }}
        >
          Abrir blog público <ExternalLink size={14} />
        </a>
      </div>

      <div className="grid-cards">
        {publishedBlogPosts.length === 0 && pendingBlogPosts.length === 0 && (
          <div className="glass-card" style={{ padding: '24px', color: 'var(--text-secondary)' }}>
            Aún no hay posts. Aprueba un artículo del Top 10 o crea un borrador desde “Aprobación”.
          </div>
        )}
        {publishedBlogPosts.map((post) => (
          <article key={post.id} className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <span className="score-tag">BLOG</span>
              <span className="status-badge status-verified">PUBLICADO</span>
            </div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '10px', lineHeight: 1.4 }}>
              {post.title}
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.55 }}>
              {(post.original_summary || post.content_html || post.source_citation || '')
                .toString()
                .replace(/<[^>]+>/g, '')
                .slice(0, 220)}
              …
            </p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {post.slug && (
                <a
                  href={getPublicPostUrl(post.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                  style={{ padding: '6px 10px', fontSize: '0.8rem', textDecoration: 'none' }}
                >
                  Ver en público
                </a>
              )}
              {post.source_url && (
                <a
                  href={post.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-link"
                >
                  Fuente original <ExternalLink size={14} />
                </a>
              )}
            </div>
          </article>
        ))}
        {pendingBlogPosts.map((post) => (
          <article key={`pending-${post.id}`} className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <span className="score-tag">BORRADOR</span>
              <span className="status-badge status-pending">{post.status}</span>
            </div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '10px' }}>{post.title}</h3>
            <div style={{ display: 'flex', gap: '8px' }}>
              {post.status === 'pending' && (
                <button className="btn btn-primary" onClick={() => approvePendingBlog(post.id)}>
                  Aprobar
                </button>
              )}
              {(post.status === 'approved' || post.status === 'pending') && (
                <button className="btn btn-secondary" onClick={() => publishPendingBlog(post.id)}>
                  Publicar
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
