from app.services.blog_seo import apply_blog_seo_defaults, categories_for_article
from app.models.editorial import BlogPost, NewsArticle


def test_apply_blog_seo_defaults_sets_author(monkeypatch):
    post = BlogPost(
        article_id=1,
        title="T",
        slug="t-1",
        content_html="<p>x</p>",
        source_url="https://ex.com",
        source_citation="cite",
        status="pending",
    )

    class FakeQuery:
        def filter(self, *a, **k):
            return self

        def first(self):
            return None

    class FakeDB:
        def query(self, model):
            return FakeQuery()

    apply_blog_seo_defaults(FakeDB(), post, article=None, reviewer="Editor A")
    assert post.author_name
    assert post.reviewer_name == "Editor A"
    assert post.seo_description


def test_categories_empty_without_article():
    class FakeDB:
        def query(self, model):
            raise AssertionError("should not query")

    assert categories_for_article(FakeDB(), None) == []
