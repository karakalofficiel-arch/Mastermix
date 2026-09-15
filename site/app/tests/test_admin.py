import tempfile
import unittest
from pathlib import Path

from app.admin import Admin, hacher, verifier, generer_mot_de_passe


class Horloge:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


class TestAdmin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.h = Horloge()
        self.admin = Admin(Path(self.tmp.name), horloge=self.h)
        self.mdp = self.admin.mot_de_passe_initial

    def tearDown(self):
        self.tmp.cleanup()

    def test_mot_de_passe_initial_genere_une_fois(self):
        self.assertEqual(len(self.mdp), 16)
        second = Admin(Path(self.tmp.name), horloge=self.h)
        self.assertIsNone(second.mot_de_passe_initial)
        self.assertIsNotNone(second.connecter(self.mdp, "1.1.1.1"))

    def test_hachage(self):
        e = hacher("abc")
        self.assertTrue(verifier("abc", e))
        self.assertFalse(verifier("abd", e))
        self.assertFalse(verifier("abc", {"sel": "zz"}))
        self.assertEqual(len(generer_mot_de_passe(20)), 20)

    def test_connexion_et_session(self):
        self.assertIsNone(self.admin.connecter("faux", "1.1.1.1"))
        jeton, csrf = self.admin.connecter(self.mdp, "1.1.1.1")
        self.assertEqual(self.admin.session_valide(jeton), csrf)
        self.assertIsNone(self.admin.session_valide("autre"))
        self.assertTrue(self.admin.csrf_valide(jeton, csrf))
        self.assertFalse(self.admin.csrf_valide(jeton, "x"))

    def test_une_seule_session(self):
        j1, _ = self.admin.connecter(self.mdp, "1.1.1.1")
        j2, _ = self.admin.connecter(self.mdp, "1.1.1.1")
        self.assertIsNone(self.admin.session_valide(j1))
        self.assertIsNotNone(self.admin.session_valide(j2))

    def test_expiration_12h(self):
        jeton, _ = self.admin.connecter(self.mdp, "1.1.1.1")
        self.h.t += 11 * 3600
        self.assertIsNotNone(self.admin.session_valide(jeton))
        self.h.t += 12 * 3600 + 1
        self.assertIsNone(self.admin.session_valide(jeton))

    def test_blocage_apres_5_echecs(self):
        for _ in range(5):
            self.assertIsNone(self.admin.connecter("faux", "9.9.9.9"))
        with self.assertRaises(PermissionError):
            self.admin.connecter(self.mdp, "9.9.9.9")
        self.assertIsNotNone(self.admin.connecter(self.mdp, "8.8.8.8"))
        self.h.t += 15 * 60 + 1
        self.assertIsNotNone(self.admin.connecter(self.mdp, "9.9.9.9"))

    def test_changer_mot_de_passe(self):
        with self.assertRaises(ValueError):
            self.admin.changer_mot_de_passe(self.mdp, "court")
        with self.assertRaises(ValueError):
            self.admin.changer_mot_de_passe("faux", "nouveau-mot-de-passe")
        self.admin.changer_mot_de_passe(self.mdp, "nouveau-mot-de-passe")
        self.assertIsNone(self.admin.connecter(self.mdp, "1.1.1.1"))
        self.assertIsNotNone(self.admin.connecter("nouveau-mot-de-passe", "1.1.1.1"))

    def test_deconnexion(self):
        jeton, _ = self.admin.connecter(self.mdp, "1.1.1.1")
        self.admin.deconnecter()
        self.assertIsNone(self.admin.session_valide(jeton))


if __name__ == "__main__":
    unittest.main()
