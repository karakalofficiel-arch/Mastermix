import unittest

from app.markdown_lite import rendre


class TestMarkdownLite(unittest.TestCase):
    def test_titres_et_paragraphes(self):
        h = rendre("# Titre\n\nUn paragraphe\nsur deux lignes.\n\n## Sous-titre\n### Petit")
        self.assertIn("<h1>Titre</h1>", h)
        self.assertIn("<p>Un paragraphe sur deux lignes.</p>", h)
        self.assertIn("<h2>Sous-titre</h2>", h)
        self.assertIn("<h3>Petit</h3>", h)

    def test_liste_et_separateur(self):
        h = rendre("- un\n- deux\n\n---\n\ntexte")
        self.assertIn("<ul><li>un</li><li>deux</li></ul>", h)
        self.assertIn("<hr>", h)
        self.assertIn("<p>texte</p>", h)

    def test_inline(self):
        h = rendre("Du **gras**, de l'*italique* et du `code`.")
        self.assertIn("<strong>gras</strong>", h)
        self.assertIn("<em>italique</em>", h)
        self.assertIn("<code>code</code>", h)

    def test_liens_surs(self):
        self.assertIn('<a href="https://ardour.org/">A</a>', rendre("[A](https://ardour.org/)"))
        self.assertIn('<a href="#">X</a>', rendre("[X](javascript:alert(1))"))
        self.assertIn('<a href="mailto:a@b.fr">M</a>', rendre("[M](mailto:a@b.fr)"))

    def test_images_limitees_a_media(self):
        self.assertIn('<img src="media/a.jpg" alt="photo" loading="lazy">', rendre("![photo](media/a.jpg)"))
        self.assertIn('<img src="media/a.jpg"', rendre("![photo](/media/a.jpg)"))
        self.assertNotIn("<img", rendre("![x](https://ailleurs.tld/a.jpg)"))
        self.assertNotIn("<img", rendre("![x](media/../secret)"))

    def test_html_echappe(self):
        h = rendre("<script>alert(1)</script> & \"quotes\"")
        self.assertNotIn("<script>", h)
        self.assertIn("&lt;script&gt;", h)
        self.assertIn("&amp;", h)

    def test_vide(self):
        self.assertEqual(rendre(""), "")
        self.assertEqual(rendre(None), "")


if __name__ == "__main__":
    unittest.main()
