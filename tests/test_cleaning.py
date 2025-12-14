from app.core.utils import normalize_text, strip_html


def test_normalize_text():
    assert normalize_text(" Hello   world\n") == "Hello world"


def test_strip_html():
    html = "<html><head><script>hack</script></head><body><h1>Titre</h1><p>Texte</p></body></html>"
    cleaned = strip_html(html)
    assert "hack" not in cleaned
    assert "Titre" in cleaned
    assert "Texte" in cleaned
