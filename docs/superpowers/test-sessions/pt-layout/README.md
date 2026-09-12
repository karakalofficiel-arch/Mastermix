# Session de test « pt-layout » (phase 2)

Créer une session 48 kHz nommée `pt-layout` avec :
- Audio 1 (mono), Audio 2 (stéréo), Inst 1 (piste MIDI + instrument ACE Reasonable Synth), bus « Aux 1reverbe », Master.
- Audio 1 : insert ACE Compressor. Inst 1 : insert ACE EQ.
- Départs Audio 1, Audio 2, Inst 1 → Aux 1reverbe.

Vérifications (cocher) :
- [ ] En-têtes : 3 colonnes INSERTS A-E / DÉPARTS A-E / E/S sur les pistes et le bus ; Master sans DÉPARTS.
- [ ] Cas 0, 3, 5 et 7 inserts sur Audio 2 : 5 slots max, tooltip « +2 inserts » sur le slot E.
- [ ] Plugin post-fader (glissé après le fader dans le mixage) absent des slots.
- [ ] Clic slot plein = fenêtre plugin ; clic droit Contourner/Retirer ; slot vide = gestionnaire de plugins.
- [ ] Départ : clic vide = menu des bus ; clic plein = fenêtre départ ; clic droit Retirer.
- [ ] Molette sur gain = ±1 dB, fader du mixage suit ; clic pan = fenêtre panoramique.
- [ ] Barre : SHUFFLE/SPOT/SLIP/GRID synchronisés avec le menu Édition ; outils zoom/main/sélecteur/crayon.
- [ ] Horloges Début/Fin/Longueur suivent la sélection.
- [ ] Règles par défaut (nouvelle session) : Mesures|Temps, Min:Sec, Code temporel, Échantillons, Tempo, Métrique, Repères.
- [ ] Colonne gauche Pistes / Groupes, Shift+E ajoute la tranche à droite de la colonne.
- [ ] Couleurs : audio bleu-gris, MIDI brun, bus vert sombre, master bordeaux ; sélection vert pomme.
- [ ] Vocabulaire : Édition, Mixage, Clips, Départ(s), Grille, Déplacer.
- [ ] Préférences > Apparence > option décochée + redémarrage = Ardour 9.8 d'origine.
- [ ] Session ouverte dans Ardour 9.8 upstream (ou l'inverse) sans erreur.

Captures : `edit-pt.png`, `edit-ardour.png` dans ce dossier.
