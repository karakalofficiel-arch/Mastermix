import os
import tempfile
import unittest
from pathlib import Path

from app.store import Store, assainir_nom, valider_slug


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.data = base / "data"
        self.www = base / "www"
        self.store = Store(self.data, self.www, contenu_defaut={"site": {"titre": "MasterMix"}})

    def tearDown(self):
        self.tmp.cleanup()

    def test_contenu_defaut_copie_au_premier_appel(self):
        self.assertEqual(self.store.lire_contenu()["site"]["titre"], "MasterMix")
        self.assertTrue((self.data / "content.json").exists())

    def test_ecriture_atomique_et_sauvegarde(self):
        nom = self.store.ecrire_contenu({"site": {"titre": "Nouveau"}})
        self.assertEqual(self.store.lire_contenu()["site"]["titre"], "Nouveau")
        self.assertIn(nom, self.store.lister_sauvegardes())
        self.assertFalse(list(self.data.glob("*.tmp")))

    def test_rotation_30_sauvegardes(self):
        for i in range(35):
            self.store.ecrire_contenu({"i": i})
        self.assertEqual(len(self.store.lister_sauvegardes()), 30)

    def test_restaurer(self):
        self.store.ecrire_contenu({"v": 1})
        nom = self.store.ecrire_contenu({"v": 2})
        self.store.ecrire_contenu({"v": 3})
        self.store.restaurer(nom)
        self.assertEqual(self.store.lire_contenu()["v"], 2)

    def test_pages(self):
        self.store.ecrire_page({"slug": "actus", "titre": "Actus", "contenu_md": "# A", "visible": True, "ordre": 2})
        self.store.ecrire_page({"slug": "aide", "titre": "Aide", "contenu_md": "", "visible": False, "ordre": 1})
        slugs = [p["slug"] for p in self.store.lister_pages()]
        self.assertEqual(slugs, ["aide", "actus"])
        self.assertEqual(self.store.lire_page("actus")["titre"], "Actus")
        self.assertIsNone(self.store.lire_page("inconnue"))
        self.assertTrue(self.store.supprimer_page("aide"))
        self.assertFalse(self.store.supprimer_page("aide"))

    def test_page_slug_invalide(self):
        with self.assertRaises(ValueError):
            self.store.ecrire_page({"slug": "../x", "titre": "x", "contenu_md": "", "visible": True, "ordre": 0})

    def test_reglages_mode_600(self):
        self.store.ecrire_reglages({"jeton": "abc"})
        self.assertEqual(self.store.lire_reglages()["jeton"], "abc")
        if os.name != "nt":
            self.assertEqual(oct((self.data / "settings.json").stat().st_mode & 0o777), "0o600")

    def test_journal(self):
        self.store.journal("1.2.3.4", "connexion")
        lignes = self.store.lire_journal()
        self.assertEqual(len(lignes), 1)
        self.assertIn("1.2.3.4", lignes[0])
        self.assertIn("connexion", lignes[0])

    def test_fichiers(self):
        (self.www / "media").mkdir(parents=True)
        (self.www / "media" / "a.png").write_bytes(b"x" * 10)
        self.assertEqual(self.store.lister_fichiers("media")[0]["taille"], 10)
        self.assertEqual(self.store.chemin_fichier("media", "../a.png").name, "a.png")
        with self.assertRaises(ValueError):
            self.store.chemin_fichier("autre", "a.png")
        self.assertTrue(self.store.supprimer_fichier("media", "a.png"))

    def test_sha256sums(self):
        d = self.www / "telechargements"
        d.mkdir(parents=True)
        (d / "x.exe").write_bytes(b"abc")
        self.store.regenerer_sha256sums()
        texte = (d / "SHA256SUMS.txt").read_text()
        self.assertIn("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad *x.exe", texte)
        self.assertEqual(self.store.lister_fichiers("telechargements")[0]["sha256"][:8], "ba7816bf")


class TestUtilitaires(unittest.TestCase):
    def test_assainir_nom(self):
        self.assertEqual(assainir_nom("Mon Fichier (1).PNG"), "Mon-Fichier-1-.PNG")
        self.assertEqual(assainir_nom("../../etc/passwd"), "passwd")
        self.assertEqual(assainir_nom(""), "fichier")

    def test_valider_slug(self):
        self.assertTrue(valider_slug("actualites-2026"))
        self.assertFalse(valider_slug("Actus"))
        self.assertFalse(valider_slug("a/b"))
        self.assertFalse(valider_slug(""))


if __name__ == "__main__":
    unittest.main()
