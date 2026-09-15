import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.mailu_api import ErreurMailu, MailuAPI, valider_partie_locale

JETON = "jeton-de-test"


class Faux(BaseHTTPRequestHandler):
    requetes = []
    users = []
    aliases = []

    def log_message(self, *a):
        pass

    def _corps(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else None

    def _repondre(self, code, obj=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if obj is not None:
            self.wfile.write(json.dumps(obj).encode("utf-8"))

    def _traiter(self):
        corps = self._corps()
        Faux.requetes.append((self.command, self.path, corps, self.headers.get("Authorization")))
        if self.headers.get("Authorization") != "Bearer " + JETON:
            return self._repondre(401, {"message": "unauthorized"})
        if self.command == "GET" and self.path == "/api/v1/user":
            return self._repondre(200, Faux.users)
        if self.command == "GET" and self.path == "/api/v1/domain/mastermix.fr":
            return self._repondre(200, {"name": "mastermix.fr"})
        if self.command == "GET" and self.path.startswith("/api/v1/domain/"):
            return self._repondre(404, {"message": "not found"})
        if self.command == "POST" and self.path == "/api/v1/user":
            if any(u["email"] == corps["email"] for u in Faux.users):
                return self._repondre(409, {"message": "exists"})
            Faux.users.append({"email": corps["email"], "displayed_name": corps["displayed_name"], "quota_bytes": corps["quota_bytes"], "enabled": True})
            return self._repondre(200, {"code": 0})
        if self.command == "PATCH" and self.path.startswith("/api/v1/user/"):
            return self._repondre(200, {"code": 0})
        if self.command == "DELETE" and self.path.startswith("/api/v1/user/"):
            email = self.path.rsplit("/", 1)[1].replace("%40", "@")
            Faux.users[:] = [u for u in Faux.users if u["email"] != email]
            return self._repondre(200, {"code": 0})
        if self.command == "GET" and self.path == "/api/v1/alias":
            return self._repondre(200, Faux.aliases)
        if self.command == "POST" and self.path == "/api/v1/alias":
            Faux.aliases.append({"email": corps["email"], "destination": corps["destination"]})
            return self._repondre(200, {"code": 0})
        if self.command == "DELETE" and self.path.startswith("/api/v1/alias/"):
            return self._repondre(200, {"code": 0})
        return self._repondre(500, {"message": "inattendu"})

    do_GET = do_POST = do_PATCH = do_DELETE = _traiter


class TestMailuAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serveur = HTTPServer(("127.0.0.1", 0), Faux)
        cls.port = cls.serveur.server_address[1]
        threading.Thread(target=cls.serveur.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()

    def setUp(self):
        Faux.requetes.clear()
        Faux.users[:] = [
            {"email": "contact@mastermix.fr", "displayed_name": "Contact", "quota_bytes": 1000, "quota_bytes_used": 10, "enabled": True},
            {"email": "admin@besancon.vip", "displayed_name": "Admin", "quota_bytes": 1000, "enabled": True},
        ]
        Faux.aliases[:] = [{"email": "support@mastermix.fr", "destination": ["contact@mastermix.fr"]}]
        self.api = MailuAPI("http://127.0.0.1:%d/api/v1" % self.port, JETON, "mastermix.fr")

    def test_verifier_domaine(self):
        self.assertEqual(self.api.verifier()["name"], "mastermix.fr")
        with self.assertRaises(ErreurMailu):
            MailuAPI("http://127.0.0.1:%d/api/v1" % self.port, JETON, "autre.fr").verifier()

    def test_jeton_refuse(self):
        with self.assertRaises(ErreurMailu) as cm:
            MailuAPI("http://127.0.0.1:%d/api/v1" % self.port, "faux", "mastermix.fr").lister_boites()
        self.assertIn("401", str(cm.exception))

    def test_lister_boites_filtre_domaine(self):
        boites = self.api.lister_boites()
        self.assertEqual([b["email"] for b in boites], ["contact@mastermix.fr"])
        self.assertEqual(boites[0]["nom"], "Contact")
        self.assertEqual(boites[0]["utilise"], 10)

    def test_creer_boite(self):
        email = self.api.creer_boite("ahmed", "MotDePasse-123456", nom="Ahmed", quota=2048)
        self.assertEqual(email, "ahmed@mastermix.fr")
        methode, chemin, corps, _ = Faux.requetes[-1]
        self.assertEqual((methode, chemin), ("POST", "/api/v1/user"))
        self.assertEqual(corps["raw_password"], "MotDePasse-123456")
        self.assertEqual(corps["displayed_name"], "Ahmed")
        self.assertEqual(corps["quota_bytes"], 2048)
        with self.assertRaises(ErreurMailu) as cm:
            self.api.creer_boite("ahmed", "x")
        self.assertIn("existe déjà", str(cm.exception))

    def test_adresse_invalide(self):
        with self.assertRaises(ErreurMailu):
            self.api.creer_boite("Ahmed Hadjadj", "x")
        self.assertFalse(valider_partie_locale("a@b"))
        self.assertTrue(valider_partie_locale("contact.pro_1"))

    def test_mot_de_passe_et_suppression(self):
        self.api.changer_mot_de_passe("contact@mastermix.fr", "Nouveau-123456")
        self.assertEqual(Faux.requetes[-1][:2], ("PATCH", "/api/v1/user/contact%40mastermix.fr"))
        self.assertEqual(Faux.requetes[-1][2], {"raw_password": "Nouveau-123456"})
        self.api.supprimer_boite("contact@mastermix.fr")
        self.assertEqual(self.api.lister_boites(), [])

    def test_alias(self):
        self.assertEqual(self.api.lister_alias()[0]["destinations"], ["contact@mastermix.fr"])
        self.api.creer_alias("ventes", ["contact@mastermix.fr", " "])
        self.assertEqual(Faux.requetes[-1][2]["destination"], ["contact@mastermix.fr"])
        with self.assertRaises(ErreurMailu):
            self.api.creer_alias("vide", [])
        self.api.supprimer_alias("ventes@mastermix.fr")
        self.assertEqual(Faux.requetes[-1][:2], ("DELETE", "/api/v1/alias/ventes%40mastermix.fr"))

    def test_injoignable(self):
        with self.assertRaises(ErreurMailu) as cm:
            MailuAPI("http://127.0.0.1:1/api/v1", JETON, "mastermix.fr").lister_boites()
        self.assertIn("injoignable", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
