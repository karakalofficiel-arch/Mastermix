"""Markdown simplifié des pages libres, converti en HTML sûr.

Pris en charge : # ## ### titres, paragraphes, listes « - », lignes « --- »,
**gras**, *italique*, [texte](url), ![alt](media/x.jpg), `code`.
Tout le reste est échappé. URL acceptées : http://, https://, /, mailto:.
Les images ne peuvent venir que de media/ (ou /media/).
"""
import html
import re

_INLINE_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_INLINE_LIEN = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_GRAS = re.compile(r"\*\*(.+?)\*\*")
_ITAL = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_CODE = re.compile(r"`([^`]+)`")
_URL_OK = re.compile(r"^(https?://|/|mailto:)", re.I)
_IMG_OK = re.compile(r"^/?media/[A-Za-z0-9._-]+$")


def _url_sure(url):
    url = url.strip()
    return url if _URL_OK.match(url) else "#"


def _inline(texte):
    texte = html.escape(texte, quote=True)

    def img(m):
        alt, src = m.group(1), html.unescape(m.group(2)).strip()
        if not _IMG_OK.match(src):
            return html.escape("![%s](%s)" % (alt, src))
        return '<img src="%s" alt="%s" loading="lazy">' % (html.escape(src.lstrip("/"), quote=True), alt)

    def lien(m):
        return '<a href="%s">%s</a>' % (html.escape(_url_sure(html.unescape(m.group(2))), quote=True), m.group(1))

    texte = _CODE.sub(lambda m: "<code>%s</code>" % m.group(1), texte)
    texte = _INLINE_IMG.sub(img, texte)
    texte = _INLINE_LIEN.sub(lien, texte)
    texte = _GRAS.sub(r"<strong>\1</strong>", texte)
    texte = _ITAL.sub(r"<em>\1</em>", texte)
    return texte


def rendre(md):
    lignes = (md or "").replace("\r\n", "\n").split("\n")
    sortie, paragraphe, liste = [], [], []

    def vider_paragraphe():
        if paragraphe:
            sortie.append("<p>%s</p>" % _inline(" ".join(paragraphe)))
            paragraphe.clear()

    def vider_liste():
        if liste:
            sortie.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _inline(e) for e in liste))
            liste.clear()

    for brute in lignes:
        ligne = brute.rstrip()
        if not ligne.strip():
            vider_paragraphe()
            vider_liste()
            continue
        titre = re.match(r"^(#{1,3})\s+(.*)$", ligne)
        if titre:
            vider_paragraphe()
            vider_liste()
            niveau = len(titre.group(1))
            sortie.append("<h%d>%s</h%d>" % (niveau, _inline(titre.group(2)), niveau))
            continue
        if ligne.strip() == "---":
            vider_paragraphe()
            vider_liste()
            sortie.append("<hr>")
            continue
        puce = re.match(r"^\s*-\s+(.*)$", ligne)
        if puce:
            vider_paragraphe()
            liste.append(puce.group(1))
            continue
        vider_liste()
        paragraphe.append(ligne.strip())
    vider_paragraphe()
    vider_liste()
    return "\n".join(sortie)
