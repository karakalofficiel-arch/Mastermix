# MasterMix build scripts (MSYS2 MINGW64)

Tous les scripts s'exécutent depuis la racine du dépôt, dans un shell MINGW64
(ou via `MSYSTEM=MINGW64 /c/msys64/usr/bin/bash.exe -lc 'cd /a/claude/mastermix && <script>'`).

| Script | Rôle |
|---|---|
| `setup-msys2.sh` | installe les paquets pacman et vérifie pkg-config |
| `build-portaudio-asio.sh` | télécharge le SDK ASIO Steinberg, compile un PortAudio statique avec ASIO dans `build/deps/prefix` |
| `build.sh [build|configure|clean]` | `waf configure` + `waf build` avec `--program-name=MasterMix` (utilise le PortAudio ASIO s'il existe) |
| `run-dev.sh [args]` | lance le binaire depuis l'arbre de build (`gtk2_ardour/ardev-win`) |
| `package-msys2.sh` | `waf i18n_mo` + `waf install` vers `build/stage`, assemble `dist/MasterMix/`, produit `dist/MasterMix-<version>-Setup-x64.exe` (NSIS) |
| `patches/` | copies des correctifs MinGW appliqués (aussi commités dans l'historique) |
| `po-protools.py` | applique le vocabulaire Pro Tools aux `fr.po` (idempotent, relancer après rebase ; tests dans `tests/`) |

Ordre habituel : `setup-msys2.sh`, `build-portaudio-asio.sh`, `build.sh`, `package-msys2.sh`.

## Notes

- Le nom du binaire (`ardour-9.8.N.exe`) suit `git describe` : N = nombre de
  commits depuis le tag `9.8`. Le packaging le renomme `MasterMix.exe`.
- Le SDK ASIO n'est jamais commité (licence Steinberg) ; seul le binaire
  compilé est distribué, comme le fait Ardour.
- Correctifs MinGW/GCC 16 nécessaires (commités) : `-mxsave` pour libpbd,
  règle `ardour.keys` sans shell cmd.exe, `--cxx17` (GCC 16 est en C++20
  par défaut, `u8""` devient `char8_t`), `--no-dr-mingw`.
- Traductions : activées par défaut sous Windows (`libs/ardour/globals.cc`),
  français si `LANGUAGE`/`LANG` absents (`gtk2_ardour/bundle_env_mingw.cc`).
- Disposition Pro Tools (phase 2) : option `use-protools-layout`
  (Préférences > Apparence, redémarrage requis). Désactivée = interface
  Ardour d'origine. Code dans `gtk2_ardour/pt_*.{h,cc}` et patchs
  conditionnels dans `route_time_axis.cc`, `editor.cc`, `editor_mixer.cc`,
  `editor_rulers.cc`, `time_axis_view.cc`, `audio_time_axis.cc`.
- Au premier démarrage d'une session, Windows peut afficher l'avertissement
  MMCSS (limite de 32 threads) : message standard d'Ardour, sans effet bloquant.

## Problèmes connus

- Tests unitaires upstream (`./waf configure --test`) : `libs/pbd/test/windows_timer_utils_test.cc`
  ne compile pas sous MinGW (`'PBD::QPC' has not been declared`, code de test
  Ardour obsolète côté Windows). Le reste de l'arbre de test compile. Non
  corrigé en phase 1 : état identique à Ardour 9.8 upstream sur Windows.
