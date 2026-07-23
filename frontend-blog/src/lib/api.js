/**
 * Cliente API del blog público (sin JWT / sin headers de tenant).
 * Admin editorial vive en Vite (:3001); este sitio es solo lectura publicada.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8012/api/v1";

export function getApiBase() {
  return API_BASE;
}

export async function fetchPublishedPosts() {
  try {
    const res = await fetch(`${API_BASE}/blog/published`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch (err) {
    console.error("fetchPublishedPosts", err);
    return [];
  }
}

export async function fetchPublishedPost(slug) {
  try {
    const res = await fetch(`${API_BASE}/blog/${encodeURIComponent(slug)}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch (err) {
    console.error("fetchPublishedPost", err);
    return null;
  }
}

export function excerptFromPost(post, max = 220) {
  const raw = (
    post?.original_summary ||
    post?.content_html ||
    post?.source_citation ||
    ""
  ).toString();
  const text = raw.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  if (!text) return "Sin extracto disponible.";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}
