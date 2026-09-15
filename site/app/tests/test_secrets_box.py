import os
import tempfile
import unittest
from pathlib import Path

from app.secrets_box import charger_cle, chiffrer, dechiffrer


class TestSecretsBox(unittest.TestCase):
    def test_cle_creee_puis_relue(self):
        with tempfile.TemporaryDirectory() as d:
            k1 = charger_cle(Path(d))
            k2 = charger_cle(Path(d))
            self.assertEqual(len(k1), 32)
            self.assertEqual(k1, k2)
            if os.name != "nt":
                self.assertEqual(oct((Path(d) / ".cle").stat().st_mode & 0o777), "0o600")

    def test_aller_retour(self):
        cle = os.urandom(32)
        boite = chiffrer(cle, "Mot de p@sse ünïcode")
        self.assertTrue(boite.startswith("v1:"))
        self.assertEqual(dechiffrer(cle, boite), "Mot de p@sse ünïcode")

    def test_nonce_different_a_chaque_fois(self):
        cle = os.urandom(32)
        self.assertNotEqual(chiffrer(cle, "x"), chiffrer(cle, "x"))

    def test_alteration_detectee(self):
        cle = os.urandom(32)
        boite = chiffrer(cle, "secret")
        parties = boite.split(":")
        parties[3] = ("0" if parties[3][0] != "0" else "1") + parties[3][1:]
        with self.assertRaises(ValueError):
            dechiffrer(cle, ":".join(parties))

    def test_mauvaise_cle(self):
        boite = chiffrer(os.urandom(32), "secret")
        with self.assertRaises(ValueError):
            dechiffrer(os.urandom(32), boite)

    def test_format_invalide(self):
        with self.assertRaises(ValueError):
            dechiffrer(os.urandom(32), "n'importe quoi")


if __name__ == "__main__":
    unittest.main()
