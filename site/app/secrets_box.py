"""Chiffrement authentifié des mots de passe de boîtes, bibliothèque standard.

Clé maîtresse de 32 octets dans data/.cle. Deux sous-clés dérivées (HKDF-SHA256) :
chiffrement (flux SHA-256 en mode compteur, XOR) et authentification (HMAC-SHA256
sur nonce + chiffré, vérifié avant tout déchiffrement). Format :
    v1:<nonce hex>:<étiquette hex>:<chiffré hex>
Protège contre la lecture du fichier de réglages seul ; ne protège pas contre
quelqu'un qui possède à la fois la clé et le fichier (même volume).
"""
import hashlib
import hmac
import os
from pathlib import Path

VERSION = "v1"


def charger_cle(data_dir):
    chemin = Path(data_dir) / ".cle"
    if chemin.exists():
        cle = chemin.read_bytes()
        if len(cle) == 32:
            return cle
    cle = os.urandom(32)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        f.write(cle)
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    os.replace(tmp, chemin)
    return cle


def _hkdf(cle, info):
    prk = hmac.new(b"mastermix-secrets-box", cle, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()


def _flux(cle_chiffrement, nonce, longueur):
    sortie = bytearray()
    compteur = 0
    while len(sortie) < longueur:
        sortie += hashlib.sha256(cle_chiffrement + nonce + compteur.to_bytes(4, "big")).digest()
        compteur += 1
    return bytes(sortie[:longueur])


def chiffrer(cle, texte):
    kc, ka = _hkdf(cle, b"chiffrement"), _hkdf(cle, b"authentification")
    nonce = os.urandom(16)
    clair = texte.encode("utf-8")
    chiffre = bytes(a ^ b for a, b in zip(clair, _flux(kc, nonce, len(clair))))
    etiquette = hmac.new(ka, nonce + chiffre, hashlib.sha256).digest()
    return ":".join([VERSION, nonce.hex(), etiquette.hex(), chiffre.hex()])


def dechiffrer(cle, boite):
    try:
        version, nonce_hex, etiquette_hex, chiffre_hex = boite.split(":")
        nonce = bytes.fromhex(nonce_hex)
        etiquette = bytes.fromhex(etiquette_hex)
        chiffre = bytes.fromhex(chiffre_hex)
    except (ValueError, AttributeError):
        raise ValueError("format de secret invalide")
    if version != VERSION or len(nonce) != 16:
        raise ValueError("format de secret invalide")
    kc, ka = _hkdf(cle, b"chiffrement"), _hkdf(cle, b"authentification")
    attendu = hmac.new(ka, nonce + chiffre, hashlib.sha256).digest()
    if not hmac.compare_digest(attendu, etiquette):
        raise ValueError("secret altéré ou clé incorrecte")
    clair = bytes(a ^ b for a, b in zip(chiffre, _flux(kc, nonce, len(chiffre))))
    return clair.decode("utf-8")
