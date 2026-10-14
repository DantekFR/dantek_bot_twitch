# Journal des décisions techniques

Format : date — décision — contexte — conséquence.

## 2026-10-09 — Toolchain uv en user-space
SteamOS est immuable (racine read-only). uv installe son binaire et ses CPython
dans ~/.local, sans root. Conséquence : zéro risque sur la machine de jeu,
lockfile reproductible.

## 2026-10-09 — Repo public, main + tags par live
Construire en public = portfolio vivant. Tags v0.x = épisodes du Dev du Vendredi.

## 2026-10-09 — Abandon IRC (twitchio 2) au profit d'EventSub (twitchio 3)
En live : les scopes IRC chat:read/chat:edit ne suffisent pas à la v3,
qui reçoit le chat via EventSub et envoie via Helix.
Conséquence : AutoBot, subscriptions, serveur OAuth local :4343.

## 2026-10-09 — App OAuth détenue par le compte streamer
Une app créée par le compte bot bloque l'autorisation channel:bot du streamer
(hors équipe de l'app). L'app appartient donc à dantekfr ; dantekos_bot
n'en est qu'un utilisateur.

## 2026-10-09 — Compte bot dédié : dantekos_bot
La v0.1 parlait avec le token du streamer (démo). v0.2 : identité séparée,
messages du bot distinguables, future modération possible.

## 2026-10-09 — Tokens en mémoire (temporaire)
AutoBot sans base : ré-autorisation via :4343 à chaque restart.
Accepté pour la démo ; persistance SQLite = épisode suivant.

## À trancher (prochains épisodes)
- Persistance des tokens (SQLite)
- Récompenses VRAM → commandes custom forgées en live (file d'attente)
- Modération auto · Mémo (Ollama) · overlay maison
