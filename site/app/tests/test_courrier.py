import imaplib
import unittest
from email.message import EmailMessage

from app import courrier
from app.courrier import Boite, ErreurCourrier, analyser_message, assainir_html, construire_message, extraire_piece


def message_test(avec_piece=True):
    m = EmailMessage()
    m["From"] = "Alice <alice@exemple.fr>"
    m["To"] = "contact@mastermix.fr"
    m["Subject"] = "Bonjour"
    m["Date"] = "Mon, 15 Sep 2026 10:00:00 +0200"
    m["Message-ID"] = "<abc@exemple.fr>"
    m.set_content("Texte brut")
    m.add_alternative("<html><body><p>Hello <b>gras</b></p><script>alert(1)</script><a href='javascript:x'>l</a><a href='https://ok.fr'>ok</a></body></html>", subtype="html")
    if avec_piece:
        m.add_attachment(b"PDFDATA", maintype="application", subtype="pdf", filename="devis.pdf")
    return m.as_bytes()


class FauxImap:
    """Double d'IMAP4_SSL : mémorise les appels, sert un message."""
    instances = []

    def __init__(self, reglages):
        self.appels = []
        self.messages = {b"1": message_test(), b"2": message_test(False)}
        FauxImap.instances.append(self)

    def login(self, u, p):
        self.appels.append(("login", u))
        if p != "bon":
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, dossier):
        self.appels.append(("select", dossier))
        return ("OK", [b"2"]) if dossier in ("INBOX", "Sent") else ("NO", [b""])

    def create(self, dossier):
        self.appels.append(("create", dossier))

    def search(self, charset, critere):
        return "OK", [b" ".join(sorted(self.messages))]

    def fetch(self, ids, parties):
        self.appels.append(("fetch", ids, parties))
        reponses = []
        for uid in ids.split(b",") if isinstance(ids, bytes) else [ids.encode()]:
            brut = self.messages[uid]
            if "HEADER.FIELDS" in parties:
                entete = b"\n".join(l for l in brut.split(b"\n\n", 1)[0].split(b"\n") if l.split(b":")[0] in (b"From", b"To", b"Subject", b"Date")) + b"\n\n"
                reponses.append((uid + b" (FLAGS (\\Seen) RFC822.SIZE 123 BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)] {0}", entete))
            else:
                reponses.append((uid + b" (BODY[] {0}", brut))
            reponses.append(b")")
        return "OK", reponses

    def store(self, id_, op, drapeau):
        self.appels.append(("store", id_, op, drapeau))
        return "OK", []

    def expunge(self):
        self.appels.append(("expunge",))
        return "OK", []

    def append(self, dossier, drapeaux, date, brut):
        self.appels.append(("append", dossier))
        return "OK", []

    def close(self):
        pass

    def logout(self):
        self.appels.append(("logout",))


class FauxSmtp:
    envoyes = []

    def __init__(self, reglages):
        pass

    def login(self, u, p):
        if p != "bon":
            import smtplib
            raise smtplib.SMTPAuthenticationError(535, b"non")

    def send_message(self, msg, from_addr, to_addrs):
        FauxSmtp.envoyes.append((msg, from_addr, to_addrs))

    def quit(self):
        pass


class TestAnalyse(unittest.TestCase):
    def test_analyser_message(self):
        m = analyser_message(message_test())
        self.assertEqual(m["sujet"], "Bonjour")
        self.assertEqual(m["de"], "Alice <alice@exemple.fr>")
        self.assertEqual(m["date"], "2026-09-15 10:00")
        self.assertEqual(m["texte"].strip(), "Texte brut")
        self.assertIn("<p>Hello <b>gras</b></p>", m["html"])
        self.assertNotIn("script", m["html"])
        self.assertNotIn("javascript", m["html"])
        self.assertIn('href="https://ok.fr"', m["html"])
        self.assertEqual(m["pieces"][0]["nom"], "devis.pdf")
        self.assertEqual(m["pieces"][0]["taille"], 7)

    def test_extraire_piece(self):
        m = analyser_message(message_test())
        nom, type_, octets = extraire_piece(message_test(), m["pieces"][0]["indice"])
        self.assertEqual((nom, type_, octets), ("devis.pdf", "application/pdf", b"PDFDATA"))
        with self.assertRaises(ErreurCourrier):
            extraire_piece(message_test(), 99)

    def test_assainir_html_images_et_style(self):
        h = assainir_html('<style>p{}</style><img src="https://pixel"><p onclick="x">ok</p>')
        self.assertEqual(h, "<p>ok</p>")

    def test_construire_message_reponse(self):
        msg = construire_message("contact@mastermix.fr", "Contact", ["a@b.fr"], ["c@d.fr"], "Re: X", "corps",
                                 [("f.txt", "text/plain", b"abc")], en_reponse_a="<abc@exemple.fr>", references="<r1@x>")
        self.assertEqual(msg["From"], "Contact <contact@mastermix.fr>")
        self.assertEqual(msg["In-Reply-To"], "<abc@exemple.fr>")
        self.assertEqual(msg["References"], "<r1@x> <abc@exemple.fr>")
        self.assertTrue(msg["Message-ID"].endswith("@mastermix.fr>"))
        self.assertEqual([p.get_filename() for p in msg.iter_attachments()], ["f.txt"])

    def test_citer(self):
        c = courrier.citer({"date": "2026-09-15 10:00", "de": "Alice", "texte": "a\nb"})
        self.assertIn("> a\n> b", c)


class TestBoite(unittest.TestCase):
    def setUp(self):
        FauxImap.instances.clear()
        FauxSmtp.envoyes.clear()
        self.boite = Boite({}, "contact@mastermix.fr", "bon", fabrique_imap_=FauxImap, fabrique_smtp_=FauxSmtp)

    def test_identifiants_incorrects(self):
        with self.assertRaises(ErreurCourrier) as cm:
            Boite({}, "contact@mastermix.fr", "faux", fabrique_imap_=FauxImap).lister()
        self.assertIn("identifiants", str(cm.exception))
        with self.assertRaises(ErreurCourrier):
            courrier.verifier_identifiants({}, "contact@mastermix.fr", "faux", fabrique=FauxImap)
        self.assertTrue(courrier.verifier_identifiants({}, "contact@mastermix.fr", "bon", fabrique=FauxImap))

    def test_lister(self):
        liste = self.boite.lister("recus")
        self.assertEqual([m["id"] for m in liste], ["2", "1"])
        self.assertEqual(liste[0]["sujet"], "Bonjour")
        self.assertTrue(liste[0]["lu"])
        self.assertEqual(liste[0]["taille"], 123)
        self.assertIn(("select", "INBOX"), FauxImap.instances[0].appels)
        self.assertIn(("logout",), FauxImap.instances[0].appels)

    def test_lire_marquer_supprimer(self):
        message, brut = self.boite.lire("recus", "1")
        self.assertEqual(message["sujet"], "Bonjour")
        self.assertEqual(message["id"], "1")
        self.boite.marquer("recus", "1", False)
        self.assertIn(("store", "1", "-FLAGS", "\\Seen"), FauxImap.instances[-1].appels)
        self.boite.supprimer("recus", "1")
        self.assertIn(("expunge",), FauxImap.instances[-1].appels)

    def test_envoyer_et_copie_envoyes(self):
        mid = self.boite.envoyer("Contact", "a@b.fr, c@d.fr", "Objet", "Corps", pieces=[("x.txt", "text/plain", b"1")])
        self.assertTrue(mid.startswith("<"))
        msg, de, a = FauxSmtp.envoyes[0]
        self.assertEqual(de, "contact@mastermix.fr")
        self.assertEqual(a, ["a@b.fr", "c@d.fr"])
        self.assertEqual(msg["Subject"], "Objet")
        self.assertIn(("append", "Sent"), FauxImap.instances[-1].appels)

    def test_envoyer_sans_destinataire(self):
        with self.assertRaises(ErreurCourrier):
            self.boite.envoyer("Contact", "pas une adresse", "x", "y")

    def test_pieces_trop_lourdes(self):
        with self.assertRaises(ErreurCourrier):
            self.boite.envoyer("Contact", "a@b.fr", "x", "y", pieces=[("g.bin", "application/octet-stream", b"0" * (20 * 1024 * 1024 + 1))])

    def test_envoi_refuse(self):
        b = Boite({}, "contact@mastermix.fr", "faux", fabrique_imap_=FauxImap, fabrique_smtp_=FauxSmtp)
        with self.assertRaises(ErreurCourrier) as cm:
            b.envoyer("C", "a@b.fr", "x", "y")
        self.assertIn("identifiants", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
