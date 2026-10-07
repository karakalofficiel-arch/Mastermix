import copy
import json
import unittest
from pathlib import Path

from app import render

INDEX = Path(__file__).resolve().parents[2] / "www" / "index.html"


class TestRender(unittest.TestCase):
    def test_contenu_defaut_reproduit_la_page_actuelle(self):
        attendu = INDEX.read_text(encoding="utf-8")
        self.assertEqual(render.page_accueil(render.CONTENU_DEFAUT), attendu)

    def test_aucun_jeton_restant(self):
        self.assertNotIn("@@", render.page_accueil(render.CONTENU_DEFAUT))

    def test_contenu_defaut_serialisable(self):
        json.dumps(render.CONTENU_DEFAUT)

    def test_echappement(self):
        c = copy.deepcopy(render.CONTENU_DEFAUT)
        c["accueil"]["titre"] = "<script>x</script>"
        h = render.page_accueil(c)
        self.assertNotIn("<script>x", h)
        self.assertIn("&lt;script&gt;x", h)

    def test_accroche_em(self):
        c = copy.deepcopy(render.CONTENU_DEFAUT)
        c["accueil"]["accroche"] = "Tout *simple*."
        self.assertIn("Tout <em>simple</em>.", render.page_accueil(c))

    def test_menu_pages_visibles_seulement(self):
        pages = [{"slug": "actus", "titre": "Actus", "visible": True}, {"slug": "brouillon", "titre": "B", "visible": False}]
        h = render.page_accueil(render.CONTENU_DEFAUT, pages)
        self.assertIn('<a href="/p/actus">Actus</a>', h)
        self.assertNotIn("brouillon", h)

    def test_taille(self):
        self.assertEqual(render.format_taille(68120243), "65 Mo")
        self.assertEqual(render.format_taille(2048), "2 Ko")
        self.assertEqual(render.format_taille("x"), "")

    def test_dix_plugins_par_defaut(self):
        noms = [p["nom"] for p in render.CONTENU_DEFAUT["plugins"]["liste"]]
        self.assertEqual(len(noms), 10)
        for absent in ("MasterBend", "MasterDrum", "MasterString"):
            self.assertNotIn(absent, noms)
        h = render.page_accueil(render.CONTENU_DEFAUT)
        self.assertNotIn("treize", h.lower())
        self.assertNotIn("Treize", h)

    def test_anneau_3d_des_plugins(self):
        h = render.page_accueil(render.CONTENU_DEFAUT)
        self.assertEqual(h.count('class="carte3d"'), 10)
        self.assertIn('style="--n:10"', h)
        self.assertEqual(h.count('plugins/masterq.jpg'), 2)   # anneau + grille
        self.assertIn('<figcaption>MasterQ</figcaption>', h)
        self.assertIn('<canvas class="onde"', h)

    def test_accueil_image_par_defaut(self):
        h = render.page_accueil(render.CONTENU_DEFAUT)
        self.assertNotIn("<video", h)
        self.assertIn('<img src="editeur.jpg"', h)

    def test_accueil_video_si_renseignee(self):
        c = copy.deepcopy(render.CONTENU_DEFAUT)
        c["accueil"]["video"] = "demo.webm"
        h = render.page_accueil(c)
        self.assertIn('<video', h)
        self.assertIn('src="media/demo.webm"', h)
        self.assertIn('poster="editeur.jpg"', h)
        self.assertIn("autoplay", h)
        self.assertIn("muted", h)
        self.assertIn("loop", h)
        self.assertIn("playsinline", h)
        self.assertNotIn('<img src="editeur.jpg"', h)

    def test_chiffres(self):
        h = render.page_accueil(render.CONTENU_DEFAUT)
        self.assertEqual(h.count('class="chiffre"'), 3)
        self.assertIn('data-valeur="8,3"', h)
        c = copy.deepcopy(render.CONTENU_DEFAUT)
        c["chiffres"]["liste"] = [["42", "x", "<b>"]]
        h = render.page_accueil(c)
        self.assertIn("&lt;b&gt;", h)
        self.assertEqual(h.count('class="chiffre"'), 1)

    def test_page_libre(self):
        page = {"slug": "actus", "titre": "Actualités", "contenu_md": "# Bonjour\n\nTexte **gras**.", "visible": True}
        h = render.page_libre(render.CONTENU_DEFAUT, page, [page])
        self.assertIn("<title>Actualités — MasterMix</title>", h)
        self.assertIn('<main class="wrap page">', h)
        self.assertIn("<strong>gras</strong>", h)
        self.assertIn('<a href="/p/actus">Actualités</a>', h)
        self.assertIn("<footer>", h)
        self.assertNotIn('class="hero"', h)


if __name__ == "__main__":
    unittest.main()
