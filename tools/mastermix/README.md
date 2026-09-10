# MasterMix build scripts (MSYS2 MINGW64)

- `setup-msys2.sh`   installe les dépendances pacman et vérifie pkg-config.
- `build.sh`         `waf configure` + `waf build` avec `--program-name=MasterMix`.
- `package-msys2.sh` assemble `dist/MasterMix/` et produit l'installeur NSIS.
- `patches/`         patches de build MinGW appliqués en commits séparés (vide si aucun).

Tous les scripts s'exécutent depuis la racine du dépôt.
