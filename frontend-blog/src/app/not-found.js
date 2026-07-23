import Link from "next/link";

export default function NotFound() {
  return (
    <main className="site-shell">
      <h1 className="brand">
        AUTORIDAD <span>360</span>
      </h1>
      <p className="lede">Esa nota no está publicada o no existe.</p>
      <Link href="/" className="back">
        ← Volver al blog
      </Link>
    </main>
  );
}
