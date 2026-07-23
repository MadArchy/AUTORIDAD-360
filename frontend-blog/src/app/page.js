import Link from "next/link";
import { excerptFromPost, fetchPublishedPosts } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function BlogHome() {
  const posts = await fetchPublishedPosts();

  return (
    <main className="site-shell">
      <header className="site-header">
        <h1 className="brand">
          AUTORIDAD <span>360</span>
        </h1>
        <p className="lede">
          Blog público de inteligencia editorial — Juan Vásquez. Solo notas
          publicadas con citación a la fuente original.
        </p>
      </header>

      {posts.length === 0 ? (
        <div className="empty">
          Aún no hay publicaciones. El equipo editorial publica desde el admin
          (Vite · puerto 3001).
        </div>
      ) : (
        <div className="post-list">
          {posts.map((post) => (
            <Link key={post.id} href={`/blog/${post.slug}`} className="post-card">
              <div className="post-meta">
                <span className="tag">Publicado</span>
                <span>
                  {post.published_at
                    ? new Date(post.published_at).toLocaleDateString("es-MX")
                    : "—"}
                </span>
              </div>
              <h2>{post.title}</h2>
              <p>{excerptFromPost(post)}</p>
            </Link>
          ))}
        </div>
      )}

      <footer className="site-footer">
        Sitio público Next.js · Admin editorial en Vite (:3001)
      </footer>
    </main>
  );
}
