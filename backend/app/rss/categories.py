"""Categorías RSS: tipologías JV + LatAm/legal + Google News RSS (sin API key)."""

# Google News RSS helpers (hl/gl México)
_GNEWS = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=MX&ceid=MX:es-419"

RSS_CATEGORIES = [
    {
        "slug": "tecnologia-ia",
        "name": "Tecnología e Inteligencia Artificial",
        "rss_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "slug": "finanzas-regulacion",
        "name": "Finanzas y Regulación",
        "rss_url": "https://www.sec.gov/news/pressreleases.rss",
    },
    {
        "slug": "compliance",
        "name": "Compliance y Cumplimiento",
        "rss_url": "https://www.complianceweek.com/rss",
    },
    {
        "slug": "derecho-corporativo",
        "name": "Derecho Corporativo",
        "rss_url": "https://feeds.feedburner.com/lawfare",
    },
    {
        "slug": "legal-tech",
        "name": "Legal Tech e IA para abogados",
        "rss_url": "https://www.lawsitesblog.com/feeds/posts/default",
    },
    {
        "slug": "propiedad-intelectual",
        "name": "Propiedad Intelectual y Patentes",
        "rss_url": "https://www.wipo.int/rss/en/news.xml",
    },
    {
        "slug": "comercio-mx-us",
        "name": "Comercio e integración MX-US",
        "rss_url": "https://www.trade.gov/rss.xml",
    },
    {
        "slug": "mexico-negocios",
        "name": "México — Negocios y Economía",
        "rss_url": "https://www.eleconomista.com.mx/rss/empresas.xml",
    },
    {
        "slug": "politica-economica",
        "name": "Política Económica y Pública",
        "rss_url": "https://feeds.bbci.co.uk/news/business/rss.xml",
    },
    {
        "slug": "privacidad-datos",
        "name": "Privacidad y datos",
        "rss_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    },
    {
        "slug": "ciberseguridad",
        "name": "Ciberseguridad empresarial",
        "rss_url": "https://feeds.feedburner.com/TheHackersNews",
    },
    # —— LatAm / breaking (Google News RSS, sin API key) ——
    {
        "slug": "gnews-ia-mx",
        "name": "Google News — IA México",
        "rss_url": _GNEWS.format(q="inteligencia+artificial+OR+IA+when:1d"),
    },
    {
        "slug": "gnews-regulacion-ia",
        "name": "Google News — Regulación IA",
        "rss_url": _GNEWS.format(
            q="regulaci%C3%B3n+inteligencia+artificial+OR+%22AI+Act%22+OR+NIST+when:1d"
        ),
    },
    {
        "slug": "gnews-legal-tech",
        "name": "Google News — Legal tech / compliance",
        "rss_url": _GNEWS.format(
            q="legal+tech+OR+compliance+IA+OR+%22general+counsel%22+AI+when:1d"
        ),
    },
    {
        "slug": "gnews-comercio-mx-us",
        "name": "Google News — Comercio MX-US / nearshoring",
        "rss_url": _GNEWS.format(
            q="nearshoring+OR+T-MEC+OR+USMCA+OR+%22M%C3%A9xico+Estados+Unidos%22+when:1d"
        ),
    },
    {
        "slug": "reuters-technology",
        "name": "Reuters — Technology",
        "rss_url": "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best",
    },
]
