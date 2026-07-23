import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchPublishedPost } from "../../../lib/api";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const post = await fetchPublishedPost(params.slug);
  if (!post) return { title: "No encontrado · AUTORIDAD 360" };
  return {
    title: `${post.title} · AUTORIDAD 360`,
    description: (post.source_citation || post.title || "").slice(0, 160),
  };
}

export default async function BlogPostPage({ params }) {
  const post = await fetchPublishedPost(params.slug);
  if (!post) notFound();

  return (
    <main className="site-shell article-page">
      <Link href="/" className="back">
        ← Volver al blog
      </Link>
      <p className="post-meta" style={{ marginBottom: 12 }}>
        <span className="tag">AUTORIDAD 360</span>
        <span>
          {post.published_at
            ? new Date(post.published_at).toLocaleDateString("es-MX", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })
            : ""}
        </span>
      </p>
      <h1>{post.title}</h1>

      <article
        className="article-body"
        dangerouslySetInnerHTML={{
          __html:
            post.content_html ||
            `<p>${(post.original_summary || "").replace(/</g, "&lt;")}</p>`,
        }}
      />

      <div className="citation">
        {post.source_citation && <p>{post.source_citation}</p>}
        {post.source_url && (
          <p>
            Fuente original:{" "}
            <a href={post.source_url} target="_blank" rel="noopener noreferrer">
              {post.source_url}
            </a>
          </p>
        )}
      </div>

      <footer className="site-footer">AUTORIDAD 360 · Blog público</footer>
    </main>
  );
}
