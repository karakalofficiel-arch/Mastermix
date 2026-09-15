import hashlib
import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from app import server
from app.tests.test_courrier import FauxImap, FauxSmtp
from app.tests.test_mailu_api import Faux as FauxMailu, JETON
from http.server import HTTPServer

RACINE = Path(__file__).resolve().parents[2]


class Client:
    def __init__(self, port):
        self.port = port
        self.cookie = None
        self.csrf = None

    def req(self, methode, chemin, corps=None, entetes=None, brut=False):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = dict(entetes or {})
        if self.cookie:
            h["Cookie"] = self.cookie
        if self.csrf:
            h["X-CSRF"] = self.csrf
        if corps is not None and not brut:
            corps = json.dumps(corps).encode("utf-8")
            h["Content-Type"] = "application/json"
        c.request(methode, chemin, body=corps, headers=h)
        r = c.getresponse()
        donnees = r.read()
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        r.donnees = donnees
        c.close()
        return r

    def json(self, methode, chemin, corps=None):
        r = self.req(methode, chemin, corps)
        try:
            return r.status, json.loads(r.donnees.decode("utf-8"))
        except ValueError:
            return r.status, r.donnees

    def connecter(self, mdp):
        code, d = self.json("POST", "/admin/api/connexion", {"mot_de_passe": mdp})
        if code == 200:
            self.csrf = d["csrf"]
        return code


class TestServeur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.www = base / "www"
        shutil.copytree(RACINE / "www", cls.www, ignore=shutil.ignore_patterns("*.exe", "*.zip"))
        (cls.www / "telechargements").mkdir(exist_ok=True)
        (cls.www / "telechargements" / "MasterMix-9.8.24-Setup-x64.exe").write_bytes(b"MZ" + b"\0" * 3000)
        server.FABRIQUES["imap"] = FauxImap
        server.FABRIQUES["smtp"] = FauxSmtp
        server.FABRIQUES["adresse_mailu"] = "127.0.0.1"
        cls.serveur = server.creer_serveur("127.0.0.1", 0, base / "data", cls.www)
        cls.port = cls.serveur.server_address[1]
        threading.Thread(target=cls.serveur.serve_forever, daemon=True).start()
        cls.mdp = server.APP.admin.mot_de_passe_initial
        cls.mailu = HTTPServer(("127.0.0.1", 0), FauxMailu)
        cls.port_mailu = cls.mailu.server_address[1]
        threading.Thread(target=cls.mailu.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()
        cls.mailu.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        self.c = Client(self.port)
        FauxMailu.users[:] = [{"email": "contact@mastermix.fr", "displayed_name": "Contact", "quota_bytes": 100, "enabled": True}]
        FauxMailu.aliases[:] = []
        FauxSmtp.envoyes.clear()

    def admin(self):
        self.assertEqual(self.c.connecter(self.mdp), 200)
        return self.c

    # --- public ------------------------------------------------------------
    def test_accueil_identique_a_index(self):
        r = self.c.req("GET", "/")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.donnees.decode("utf-8"), (RACINE / "www" / "index.html").read_text(encoding="utf-8"))

    def test_healthz_et_404(self):
        self.assertEqual(self.c.req("GET", "/healthz").donnees, b"ok\n")
        self.assertEqual(self.c.req("GET", "/inconnu.html").status, 404)
        self.assertEqual(self.c.req("GET", "/../app/server.py").status, 404)
        self.assertEqual(self.c.req("GET", "/p/inconnue").status, 404)
        self.assertEqual(self.c.req("POST", "/").status, 405)

    def test_statique_et_telechargement(self):
        r = self.c.req("GET", "/logo.svg")
        self.assertEqual(r.getheader("Content-Type"), "image/svg+xml")
        r = self.c.req("HEAD", "/telechargements/MasterMix-9.8.24-Setup-x64.exe")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.getheader("Content-Length"), "3002")
        self.assertIn("attachment", r.getheader("Content-Disposition"))
        r = self.c.req("GET", "/telechargements/MasterMix-9.8.24-Setup-x64.exe", entetes={"Range": "bytes=0-1"})
        self.assertEqual(r.status, 206)
        self.assertEqual(r.donnees, b"MZ")
        self.assertEqual(r.getheader("Content-Range"), "bytes 0-1/3002")
        self.assertEqual(self.c.req("GET", "/telechargements/").status, 404)

    # --- admin -------------------------------------------------------------
    def test_admin_page_et_acces(self):
        r = self.c.req("GET", "/admin")
        self.assertEqual(r.status, 200)
        self.assertIn(b"Administration", r.donnees)
        self.assertEqual(self.c.json("GET", "/admin/api/etat")[0], 401)
        self.assertEqual(self.c.connecter("faux"), 401)
        self.assertEqual(self.c.connecter(self.mdp), 200)
        code, d = self.c.json("GET", "/admin/api/etat")
        self.assertEqual(code, 200)
        self.assertTrue(d["mot_de_passe_initial"])

    def test_csrf_obligatoire(self):
        c = self.admin()
        csrf = c.csrf
        c.csrf = None
        self.assertEqual(c.json("PUT", "/admin/api/contenu", {})[0], 403)
        c.csrf = csrf
        self.assertEqual(c.json("PUT", "/admin/api/contenu", {})[0], 400)

    def test_contenu_modifie_visible_en_ligne_et_restaure(self):
        c = self.admin()
        code, d = c.json("GET", "/admin/api/contenu")
        contenu = d["contenu"]
        contenu["accueil"]["titre"] = "MasterMix TEST"
        code, d = c.json("PUT", "/admin/api/contenu", contenu)
        self.assertEqual(code, 200)
        self.assertIn(b"<h1>MasterMix TEST</h1>", self.c.req("GET", "/").donnees)
        code, s = c.json("GET", "/admin/api/sauvegardes")
        self.assertGreaterEqual(len(s["sauvegardes"]), 1)
        contenu["accueil"]["titre"] = "MasterMix"
        c.json("PUT", "/admin/api/contenu", contenu)
        self.assertIn(b"<h1>MasterMix</h1>", self.c.req("GET", "/").donnees)

    def test_pages(self):
        c = self.admin()
        code, d = c.json("PUT", "/admin/api/pages/actus", {"titre": "Actualités", "contenu_md": "# Hello\n\n**gras**", "visible": True, "ordre": 1})
        self.assertEqual(code, 200)
        accueil = self.c.req("GET", "/").donnees
        self.assertIn(b'<a href="/p/actus">Actualit', accueil)
        r = self.c.req("GET", "/p/actus")
        self.assertEqual(r.status, 200)
        self.assertIn(b"<strong>gras</strong>", r.donnees)
        c.json("PUT", "/admin/api/pages/actus", {"titre": "Actualités", "contenu_md": "x", "visible": False, "ordre": 1})
        self.assertEqual(self.c.req("GET", "/p/actus").status, 404)
        self.assertEqual(c.json("PUT", "/admin/api/pages/Bad%20Slug", {"titre": "x"})[0], 400)
        self.assertEqual(c.json("DELETE", "/admin/api/pages/actus")[0], 200)
        self.assertEqual(c.json("DELETE", "/admin/api/pages/actus")[0], 404)

    def test_televersement_par_morceaux(self):
        c = self.admin()
        donnees = bytes(range(256)) * 5000        # 1,28 Mo -> 2 morceaux
        h = hashlib.sha256(donnees).hexdigest()
        morceau = 1024 * 1024
        for i, debut in enumerate(range(0, len(donnees), morceau)):
            r = c.req("POST", "/admin/api/fichiers/telechargements/morceau?nom=Test%%20Setup.exe&id=abc123&indice=%d&total=2" % i,
                      donnees[debut:debut + morceau], {"Content-Type": "application/octet-stream"}, brut=True)
            self.assertEqual(r.status, 200, r.donnees)
        d = json.loads(r.donnees)
        self.assertEqual(d["nom"], "Test-Setup.exe")
        self.assertEqual(d["sha256"], h)
        self.assertEqual(d["taille"], len(donnees))
        code, liste = c.json("GET", "/admin/api/fichiers/telechargements")
        self.assertIn(h, [f.get("sha256") for f in liste["fichiers"]])
        self.assertIn(h.encode(), self.c.req("GET", "/telechargements/SHA256SUMS.txt").donnees)
        r = c.req("POST", "/admin/api/fichiers/media/morceau?nom=x.exe&id=zz&indice=0&total=1", b"x", {"Content-Type": "application/octet-stream"}, brut=True)
        self.assertEqual(r.status, 400)
        r = c.req("POST", "/admin/api/fichiers/media/morceau?nom=a.svg&id=sv&indice=0&total=1", b"<svg onload='x'></svg>", {"Content-Type": "application/octet-stream"}, brut=True)
        self.assertEqual(r.status, 400)
        self.assertEqual(c.json("DELETE", "/admin/api/fichiers/telechargements/Test-Setup.exe")[0], 200)
        self.assertEqual(c.json("DELETE", "/admin/api/fichiers/telechargements/MasterMix-9.8.24-Setup-x64.exe")[0], 409)

    def test_reglages_et_mot_de_passe(self):
        c = self.admin()
        code, d = c.json("PUT", "/admin/api/reglages", {"mailu_url": "http://127.0.0.1:%d/api/v1/" % self.port_mailu, "mailu_jeton": JETON, "hote": "", "nom_certificat": ""})
        self.assertEqual(code, 200)
        code, d = c.json("GET", "/admin/api/reglages")
        self.assertTrue(d["mailu_jeton_defini"])
        self.assertEqual(d["hote"], "192.168.1.166")
        self.assertNotIn(JETON, json.dumps(d))
        code, d = c.json("POST", "/admin/api/reglages/tester-mailu", {})
        self.assertEqual(d["domaine"], "mastermix.fr")
        self.assertEqual(c.json("POST", "/admin/api/mot-de-passe", {"ancien": self.mdp, "nouveau": "court"})[0], 400)
        self.assertEqual(c.json("POST", "/admin/api/mot-de-passe", {"ancien": self.mdp, "nouveau": self.mdp + "-2"})[0], 200)
        self.assertEqual(c.json("POST", "/admin/api/mot-de-passe", {"ancien": self.mdp + "-2", "nouveau": self.mdp})[0], 200)
        code, d = c.json("GET", "/admin/api/journal")
        self.assertTrue(any("mot de passe admin" in l for l in d["journal"]))

    def test_adresses_et_courrier(self):
        c = self.admin()
        c.json("PUT", "/admin/api/reglages", {"mailu_url": "http://127.0.0.1:%d/api/v1" % self.port_mailu, "mailu_jeton": JETON})
        code, d = c.json("GET", "/admin/api/adresses")
        self.assertEqual(code, 200)
        self.assertEqual(d["boites"][0]["email"], "contact@mastermix.fr")
        self.assertFalse(d["boites"][0]["ouvrable"])
        # rattacher avec un mauvais mot de passe puis le bon
        self.assertEqual(c.json("POST", "/admin/api/adresses/contact@mastermix.fr/rattacher", {"mot_de_passe": "faux"})[0], 502)
        self.assertEqual(c.json("POST", "/admin/api/adresses/contact@mastermix.fr/rattacher", {"mot_de_passe": "bon"})[0], 200)
        code, d = c.json("GET", "/admin/api/adresses/ouvrables")
        self.assertEqual([b["email"] for b in d["boites"]], ["contact@mastermix.fr"])
        # créer une boîte, mot de passe généré
        code, d = c.json("POST", "/admin/api/adresses", {"local": "ahmed", "nom": "Ahmed", "quota": 2048})
        self.assertEqual(code, 200, d)
        self.assertEqual(d["email"], "ahmed@mastermix.fr")
        self.assertEqual(len(d["mot_de_passe"]), 16)
        self.assertEqual(c.json("POST", "/admin/api/adresses", {"local": "ahmed"})[0], 502)
        self.assertEqual(c.json("POST", "/admin/api/adresses", {"local": "x", "mot_de_passe": "court"})[0], 400)
        # alias
        self.assertEqual(c.json("POST", "/admin/api/alias", {"local": "support", "destinations": ["contact@mastermix.fr"]})[0], 200)
        self.assertEqual(c.json("DELETE", "/admin/api/alias/support@mastermix.fr")[0], 200)
        self.assertEqual(c.json("DELETE", "/admin/api/alias/x@ailleurs.fr")[0], 400)
        # courrier
        code, d = c.json("GET", "/admin/api/courrier/contact@mastermix.fr/recus")
        self.assertEqual(code, 200)
        self.assertEqual(d["messages"][0]["sujet"], "Bonjour")
        code, m = c.json("GET", "/admin/api/courrier/contact@mastermix.fr/recus/1")
        self.assertEqual(m["de"], "Alice <alice@exemple.fr>")
        self.assertIn("> Texte brut", m["citation"])
        r = c.req("GET", "/admin/api/courrier/contact@mastermix.fr/recus/1/piece/%d" % m["pieces"][0]["indice"])
        self.assertEqual(r.donnees, b"PDFDATA")
        self.assertIn("devis.pdf", r.getheader("Content-Disposition"))
        self.assertEqual(c.json("POST", "/admin/api/courrier/contact@mastermix.fr/recus/1/lu", {"lu": False})[0], 200)
        code, d = c.json("POST", "/admin/api/courrier/contact@mastermix.fr/envoyer",
                         {"a": "bob@exemple.fr", "sujet": "Re: Bonjour", "texte": "Merci", "en_reponse_a": m["message_id"],
                          "pieces": [{"nom": "n.txt", "type": "text/plain", "b64": "YWJj"}], "transfert_de": {"dossier": "recus", "id": "1"}})
        self.assertEqual(code, 200, d)
        msg, de, a = FauxSmtp.envoyes[-1]
        self.assertEqual(a, ["bob@exemple.fr"])
        self.assertEqual(msg["In-Reply-To"], "<abc@exemple.fr>")
        self.assertEqual(sorted(p.get_filename() for p in msg.iter_attachments()), ["devis.pdf", "n.txt"])
        self.assertEqual(c.json("DELETE", "/admin/api/courrier/contact@mastermix.fr/recus/1")[0], 200)
        self.assertEqual(c.json("GET", "/admin/api/courrier/inconnue@mastermix.fr/recus")[0], 502)
        # suppression de boîte
        self.assertEqual(c.json("DELETE", "/admin/api/adresses/ahmed@mastermix.fr")[0], 200)
        code, d = c.json("GET", "/admin/api/adresses/ouvrables")
        self.assertNotIn("ahmed@mastermix.fr", [b["email"] for b in d["boites"]])

    def test_deconnexion(self):
        c = self.admin()
        self.assertEqual(c.json("POST", "/admin/api/deconnexion", {})[0], 200)
        self.assertEqual(c.json("GET", "/admin/api/etat")[0], 401)


if __name__ == "__main__":
    unittest.main()
