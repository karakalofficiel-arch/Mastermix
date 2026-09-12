# MasterMix — Phase 2 : disposition Pro Tools, fenêtre Édition

Auteur : Ahmed Hadjadj
Date : 2026-09-12
Statut : validé
Phase précédente : `2026-09-10-mastermix-phase1-design.md` (fork, rebrand, thème, build Windows)

## 1. Objectif

Donner à MasterMix l'organisation de la fenêtre **Édition** de Pro Tools
(référence : deux captures fournies le 2026-09-12, Pro Tools en français,
fenêtres Édition et Mixage), en gardant le thème vert pomme / noir de la
phase 1. Aucune fonction d'Ardour retirée. Tout le code ajouté est
conditionné par un profil, désactivable pour retrouver l'interface Ardour.

Phase 2 = fenêtre Édition uniquement. Les phases 3 (Mixage) et 4 (fenêtres
flottantes Transport et Départ) sont esquissées en §10 et auront leur propre
spec.

Décisions prises le 2026-09-12 :

- Thème : vert pomme / noir conservé. Pas de thème gris/bleu Avid.
- Fidélité : clone structurel (nouveaux widgets C++ dans `gtk2_ardour/`).
- Ordre : Édition, puis Mixage, puis Transport + Départ.
- Vocabulaire : termes Pro Tools dans l'interface française.
- Colonnes Inserts/Départs/E/S : approche « widget de colonnes dans
  l'en-tête de piste » (approche A), pas de panneau synchronisé séparé, pas
  de réutilisation de `ProcessorBox` dans l'en-tête.

## 2. Contraintes

- Mêmes contraintes que la phase 1 : GPLv2+, en-tête `Copyright (C) 2026
  Ahmed Hadjadj` sur tout nouveau fichier, formats de session inchangés,
  toolchain MSYS2 MINGW64.
- Rebase upstream : privilégier des **fichiers nouveaux** et des patchs
  courts conditionnés par le profil (§3), sur le modèle des branches
  `Profile->get_mixbus()` déjà présentes dans `route_time_axis.cc`,
  `mixer_strip.cc`, `editor.cc`.
- Aucun nouveau mode d'édition, aucun nouvel outil : les boutons Pro Tools
  sont des habillages d'actions Ardour existantes.
- Pas de test unitaire GTK dans `gtk2_ardour` (état upstream). La
  vérification GUI est manuelle et scriptée (§9). La logique non GTK
  (scripts Python, tri des slots) est testée.

## 3. Profil « disposition Pro Tools »

- Nouvelle variable `UIConfiguration` booléenne `use-protools-layout`
  (`gtk2_ardour/ui_config_vars.inc.h`), défaut `true`.
- Exposée dans Préférences > Apparence sous « Disposition Pro Tools
  (redémarrage requis) ».
- Accès : `UIConfiguration::instance().get_use_protools_layout()`. Lue une
  fois au démarrage dans chaque constructeur concerné ; pas de
  reconstruction dynamique de l'interface.
- Quand `false` : aucun widget de phase 2 n'est créé, `controls_table`,
  barre d'outils, règles et notebook restent ceux d'Ardour. Le vocabulaire
  fr.po (§8) et les couleurs de pistes (§7) s'appliquent dans les deux cas
  (ce sont des données, pas de la disposition).

## 4. `PTTrackColumns` : Inserts / Départs / E/S dans l'en-tête de piste

### 4.1 Fichiers

- Créer : `gtk2_ardour/pt_track_columns.h`, `gtk2_ardour/pt_track_columns.cc`.
- Créer : `gtk2_ardour/pt_slot_model.h`, `gtk2_ardour/pt_slot_model.cc`
  (logique pure sans GTK, testable : `collect_insert_slots`,
  `collect_send_slots`).
- Modifier : `gtk2_ardour/route_time_axis.h/.cc` (instanciation, attache
  dans `controls_table`, connexion des signaux), `gtk2_ardour/wscript`
  (sources), `gtk2_ardour/time_axis_view.cc` (hauteur minimale sous profil).

### 4.2 Structure

`PTTrackColumns : public Gtk::HBox`, construit avec `RouteUI&` (accès à
`route()`, `gm` GainMeter, `PannerUI`, `IOButton`) et `ARDOUR::Session*`.
Trois blocs, chacun un `Gtk::VBox` avec un en-tête texte (« INSERTS A-E »,
« DÉPARTS A-E », « E/S ») :

| Bloc | Contenu | Largeur |
|---|---|---|
| Inserts | 5 `ArdourButton` empilés, slots A-E | 72 px |
| Départs | 5 `ArdourButton` empilés, slots A-E | 72 px |
| E/S | `IOButton` entrée, `IOButton` sortie, affichage gain (dB), affichage pan | 84 px |

Largeurs multipliées par `UIConfiguration::get_ui_scale()`.

Attache dans `RouteTimeAxisView` : `controls_table.attach (*_pt_columns,
5, 6, 0, 3, FILL, FILL)` (colonne après le bloc automation/playlist, sur
les trois lignes). `Editor::reset_controls_layout_width()` recalcule
automatiquement la largeur du panneau d'en-têtes.

### 4.3 Slots Inserts

- Modèle (`pt_slot_model`) : `collect_insert_slots (Route&) ->
  std::vector<InsertSlot>` parcourt `Route::processors()` dans l'ordre,
  retient les `PluginInsert` **pré-fader**, tronque à 5. `InsertSlot` =
  `{ std::weak_ptr<Processor>, std::string label, bool active }`. Le label
  est le nom du plugin tronqué à 10 caractères (points de suspension).
- Rendu : slot plein = texte du label, LED verte si actif, LED éteinte si
  contourné (bypass). Slot vide = bouton sans texte, fond `widget:bg`.
- Clic gauche slot plein : ouvre l'interface du plugin. Réutilise
  `ProcessorBox::edit_processor` du `ProcessorBox` de la route quand un
  mixer strip existe (`Mixer_UI::strip_by_route`), sinon crée un
  `ProcessorWindowProxy` propre (même mécanisme que `processor_box.cc`).
- Clic gauche slot vide : ouvre `PluginSelector` (`ARDOUR_UI::plugin_selector`)
  ; le plugin choisi est inséré pré-fader en fin de liste via
  `Route::add_processor_by_index`.
- Clic droit slot plein : menu `Contourner`/`Activer`, `Retirer`,
  `Remplacer…`. Clic droit slot vide : rien.
- Si plus de 5 inserts : tooltip du slot E « +N inserts, voir le mixage ».
- Mise à jour : `Route::processors_changed` et
  `Processor::ActiveChanged` → `refresh()` (GUI thread, via
  `gui_context()`).

### 4.4 Slots Départs

- Modèle : `collect_send_slots (Route&)` retient les `InternalSend` et
  `Send` externes, ordre des processeurs, tronqué à 5. `SendSlot` =
  `{ std::weak_ptr<Send>, std::string label, bool active, bool pre_fader }`.
  Label = nom de la route cible pour `InternalSend`
  (`target_route()->name()`, tronqué à 10), nom du send sinon.
- Slot plein : clic gauche ouvre `SendUIWindow` (existant, `send_ui.h`) ;
  en phase 4 remplacé par `PTSendWindow`. Clic droit : menu `Pré-fader`
  (coche), `Retirer`.
- Slot vide : clic gauche ouvre un menu listant les bus audio de la session
  (hors la route elle-même), sélection = `Route::add_aux_send`.
- Mise à jour : `Route::processors_changed`, `Send::ActiveChanged`.

### 4.5 Bloc E/S

- `IOButton input_button (true)` et `IOButton output_button (false)`
  construits comme dans `mixer_strip.cc` (`set_route`), donc mêmes menus
  de connexion.
- Affichage gain : `GainMeter` est déjà attaché ailleurs dans l'en-tête
  (`gm.get_gain_slider()`, `gm.get_level_meter()`), donc pas de réemploi de
  `gain_display`. Un `ArdourButton` propre affiche
  `gain_control()->get_value()` en dB, mis à jour sur `Changed` ; clic
  gauche ouvre une entrée numérique (`Gtk::Entry` inline, comme
  `gain_display` du mixer).
- Affichage pan : `ArdourButton` en lecture seule, texte « ‹100  100› »
  (stéréo) ou « pan  0 » (mono), depuis `Route::panner_shell()`. Clic
  ouvre le `PannerUI` dans une petite `ArdourWindow` flottante.

### 4.6 Types de piste

| Type | Inserts | Départs | E/S |
|---|---|---|---|
| Piste audio | oui | oui | entrée, sortie, gain, pan |
| Piste MIDI / instrument | oui | oui | entrée MIDI, sortie, gain, pan |
| Bus audio (aux) | oui | oui | entrée (« Aux 1reverbe » = nom du bus, non cliquable), sortie, gain, pan |
| Master | oui | non (bloc vide masqué) | sortie, gain |
| Monitor, VCA, foldback | aucune colonne | | |

### 4.7 Hauteur de piste

Sous profil, `TimeAxisView::preset_height (HeightNormal)` renvoie la
hauteur nécessaire à 5 slots (5 × 16 px + en-tête 14 px + marges, ×
`ui_scale`), soit environ 100 px au lieu de 60. Les hauteurs `Small` et
inférieures masquent `PTTrackColumns` (`hide()`), comme Ardour masque déjà
certains boutons. `Large` et au-dessus l'affichent.

### 4.8 Sélection et couleur

`PTTrackColumns` transmet les clics non consommés à `controls_ebox` (même
comportement que les autres boutons de l'en-tête : sélection de la piste).
Le fond suit `controls_base_selected_name` / `unselected_name`.

## 5. Barre d'outils Édition

Fichier : `gtk2_ardour/editor.cc` (`setup_toolbar`, ~l. 2728-2904), nouveau
`gtk2_ardour/pt_edit_modes.h/.cc` pour le bloc de modes.

Sous profil, `toolbar_hbox` est remplie dans cet ordre (gauche à droite) :

1. **Modes** (`PTEditModes`, grille 2×2) :
   - `SHUFFLE` = `EditMode::Ripple` (action `Editor/set-edit-ripple`),
   - `SPOT` = `EditMode::Lock` (`set-edit-lock`),
   - `SLIP` = `EditMode::Slide` (`set-edit-slide`),
   - `GRID` = toggle entre les actions `snap-magnetic` et `snap-off`
     (`editing_context.cc:533-535`) ; `cycle-snap-mode` n'est pas utilisé.
   Shuffle/Spot/Slip exclusifs, `GRID` indépendant (comme Pro Tools). Le
   `ripple_mode_selector` d'Ardour (Selected/All/Interview) reste accessible
   par clic droit sur `SHUFFLE`.
2. **Outils** (boutons `mouse_mode_box` existants, réordonnés, actions du
   groupe `Editor` dans `editing_context.cc:508-514`) : zoom
   (`zoom-to-selection`, bouton d'action simple), main
   (`set-mouse-mode-object`), sélecteur (`set-mouse-mode-range`), crayon
   (`set-mouse-mode-draw`). Le trim Pro Tools n'a pas d'outil distinct dans
   Ardour (le mode Objet trime aux bords des clips) : pas de bouton Trim.
   Le scrub n'a pas d'action de mode souris en 9.8 : pas de bouton Scrub.
   Boutons TimeFX, Content, Cut, Grid d'Ardour retirés de la barre
   (toujours accessibles par raccourci et menu).
3. **Compteur principal** : `primary_clock` d'Ardour (déjà `MainClock`),
   mode Mesures|Temps par défaut sous profil.
4. **Sélection** : trois `AudioClock` `_sel_start_clock`, `_sel_end_clock`,
   `_sel_length_clock`, étiquettes « Début », « Fin », « Longueur »,
   liés à `Selection::TimeChanged` ; lecture seule. La ligne « Curseur /
   niveau » de Pro Tools est reportée en phase 4.
5. **Grille / Déplacer** : `grid_type_selector` (étiquette « Grille ») et
   `nudge_clock` (étiquette « Déplacer »), empilés verticalement.
6. Reste de la barre d'outils Ardour (zoom box, `edit_point_selector`)
   conservé à droite.

Le `ApplicationBar` (transport, mini-timeline, mètre) est inchangé en
phase 2.

## 6. Règles

Fichier : `gtk2_ardour/editor_rulers.cc`, `editor.cc` (`set_state`).

Sous profil, quand la session n'a pas d'état `Editor` sauvegardé
(nouvelle session), les règles visibles sont, via les actions du groupe
`Rulers` (`editor_actions.cc:576-603`) : `toggle-bbt-ruler`
(Mesures|Temps), `toggle-minsec-ruler`, `toggle-timecode-ruler`,
`toggle-samples-ruler`, `toggle-tempo-ruler`, `toggle-meter-ruler`
(Métrique), `toggle-marker-ruler` (Marqueurs). Masquées :
`toggle-range-ruler`, `toggle-arrangement-ruler`, `toggle-video-ruler`.
Ordre = ordre upstream. Aucun nouveau nom d'action.

## 7. Listes latérales et couleurs de piste

### 7.1 Notebook

`editor.cc:690-707`. Sous profil :

- Pages affichées : `Pistes` (`_routes`), `Clips` (page `_regions`,
  intitulé « Clips »), `Groupes` (`_route_groups`).
- Les autres pages (Sources, Clips-triggers, Arrangement, Instantanés,
  Marqueurs, Outils MIDI) restent créées mais retirées du notebook ; elles
  sont accessibles via le menu Affichage > Listes de l'éditeur (actions
  existantes `show-editor-list` + `editor-list-page`).
- Disposition : **gauche** du canevas, un `Gtk::VPaned` nouveau avec
  Pistes en haut et Groupes en bas (séparateur ajustable), comme Pro
  Tools ; **droite** du canevas, le notebook existant réduit à la page
  Clips. Le panneau gauche est nouveau (Ardour n'a que la liste de droite)
  et s'insère dans la construction des panes de `editor.cc`
  (`edit_pane`), largeur sauvegardée dans l'état de l'éditeur
  (`pt-left-list-width`, défaut 110 px × `ui_scale`).

### 7.2 Couleurs de piste par type

`mastermix-branding/palette.py` (substitutions de `dark-ardour.colors`) :

| Alias | Valeur | Rôle |
|---|---|---|
| `audio track base` | `#1C2733` | bleu-gris sombre (audio) |
| `midi track base` | `#332A1C` | brun sombre (instrument / MIDI) |
| `audio bus base` | `#1F2E14` | vert sombre (aux) |
| `master track base` (nouvel alias si absent, sinon `theme:bg` du master) | `#33141C` | bordeaux sombre |
| `midi bus base` | `#2A2E14` | olive sombre |

Modifiers alpha existants conservés. Texte `#E8E8E8` sur ces fonds ≥ 7:1
(vérifié par `test_palette.py`). La sélection reste vert pomme.

## 8. Vocabulaire Pro Tools (fr.po)

- Créer : `tools/mastermix/po-protools.py` + `tools/mastermix/po-protools.toml`
  (table `msgid` → `msgstr` de remplacement, par domaine), tests
  `tools/mastermix/tests/test_po_protools.py`.
- Le script lit les `.po` upstream (`gtk2_ardour/po/fr.po`,
  `libs/ardour/po/fr.po`), applique la table, écrit les `.po` modifiés
  (commités), vérifie avec `msgfmt --check`. Idempotent, relançable après
  rebase.
- Table initiale (extensible pendant l'implémentation, uniquement des
  chaînes visibles dans l'Édition/Mixage) :

| msgid (extrait) | msgstr actuel | msgstr MasterMix |
|---|---|---|
| `Sends`, `Send`, `Aux Sends`, `Show Sends` | Envois… | Départs, Départ, Départs aux, Afficher les départs |
| `Regions`, `Region` | Régions, Région | Clips, Clip |
| `Mixer` | Console de mixage | Mixage |
| `Editor` | Éditeur | Édition |
| `Bars:Beats` | Mesures : temps | Mesures\|Temps |
| `Tracks & Busses` | Pistes et bus | Pistes |
| `Count-in`, `Count In` | Décompte (à vérifier) | Décompte |
| `Insert`, `Inserts` | Insert(s) | inchangé |
| `Nudge` | Décalage | Déplacer |
| `Snap`, `Grid` | Aimanter, La grille | Grille |
| `Slide`, `Ripple`, `Lock` (modes) | Glisser, Ondulation, Verrouiller | Slip, Shuffle, Spot |

- Les chaînes nouvelles de MasterMix (« INSERTS A-E », « DÉPARTS A-E »,
  « E/S », « Début », « Fin », « Longueur », « Disposition Pro Tools ») sont
  écrites avec `_()` en anglais dans le code et traduites dans `fr.po` par
  le même script (section `additions` de la table), pour que `waf i18n_pot`
  ne les perde pas.

## 9. Vérification

1. `pytest` : `mastermix-branding/tests` (couleurs, contraste),
   `tools/mastermix/tests` (po-protools : idempotence, `msgfmt --check`,
   toutes les entrées de la table trouvées).
2. `pt_slot_model` : logique de tri sans dépendance GTK. `gtk2_ardour` n'a
   pas de harnais de tests upstream ; la logique est vérifiée par la
   session de test manuelle (point 3) avec les cas : 0, 3, 5 et 7 inserts ;
   sends internes et externes mélangés à des plugins ; plugin post-fader
   (ignoré). Pas de cible cppunit ajoutée en phase 2.
3. `./waf build` sans erreur ; `run-dev.sh` ; session de test
   `docs/superpowers/test-sessions/pt-layout/` (5 pistes : Audio 1,
   Audio 2, Inst 1, Aux 1reverbe, Master 1 ; un plugin sur Audio 1 et Inst
   1 ; départs Audio 1/2/Inst 1 → Aux) : captures Édition à comparer avec
   la référence.
4. Bascule `use-protools-layout = false`, redémarrage : interface Ardour
   9.8 upstream (captures).
5. Session Ardour existante ouverte dans MasterMix et inversement : aucun
   changement de format.
6. Livrable : en fin de phase, `build.sh` puis `package-msys2.sh`
   régénèrent `dist/MasterMix/` (exe portable) et
   `dist/MasterMix-<version>-Setup-x64.exe` (demande utilisateur du
   2026-09-12 : « met à jour l'exe »).

## 10. Phases suivantes (hors périmètre, pour mémoire)

- **Phase 3 – Mixage** : `mixer_strip.cc` (`global_vpacker`, l. 335-364)
  réordonné sous profil : Inserts A-E, Départs A-E, E/S, Auto, groupe, pan,
  rec/entrée, S/M, fader + mètre gradué, valeur, nom, bloc rtd / +/- / cmp
  (latence `Route::signal_latency()`, compensation
  `Session::worst_latency_preroll()`). Largeur de tranche fixe type PT.
- **Phase 4 – Fenêtres flottantes** : `PTTransportWindow` (dérivé de
  `BigTransportWindow` : pré-roll/post-roll, fondu d'entrée, compteurs,
  décompte, métrique, tempo, GEN MTC, mètre) ; `PTSendWindow` remplaçant
  `SendUIWindow` (en-tête piste/slot/cible, SAFE/PRE/FMP, lien, pan, M,
  fader + mètre, S piste, AUTO). Ligne « Curseur / niveau » de la barre
  d'outils.

## 11. Hors périmètre phase 2

- Édition des compteurs Début/Fin/Longueur au clavier.
- Fenêtres flottantes Transport et Départ (phase 4).
- Mixage (phase 3).
- Automation « dyn / lire » en colonne : le sélecteur d'automation d'Ardour
  (`automation_button`) reste tel quel.
- Thème gris/bleu Avid.
