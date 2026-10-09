# DanTek Bot — les outils de la chaîne, codés en live

Bot Twitch maison né pendant le Dev du Vendredi : commandes, modération,
récompenses VRAM et (bientôt) une IA locale nommée Mémo.
Conçu pour tourner 24/7 sur un Steam Deck.

## Stack
- Python 3.13 · uv (toolchain user-space, SteamOS immuable)
- twitchio 3 (AutoBot + EventSub Chat)
- SQLite (mémoire & commandes custom — à venir)
- Ollama local (Mémo — à venir)
- Hôte : Steam Deck, dev via VS Code Remote-SSH

## Architecture (vue d'ensemble)
Twitch EventSub (chat) ──> AutoBot (Steam Deck) ──> components / modules
        ^                          │
        └──── envoi messages ──────┘
OAuth : mini-serveur local :4343 hébergé par le bot lui-même

## Installation
cp .env.example .env    # CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID, CHANNEL
uv sync
uv run python -m dantek_bot_twitch.main
# Bot tournant, autorisations :
#   fenêtre privée (compte bot) : http://localhost:4343/oauth?scopes=user:read:chat%20user:write:chat%20user:bot&force_verify=true
#   fenêtre normale (streamer)  : http://localhost:4343/oauth?scopes=channel:bot&force_verify=true

## Roadmap
Voir les issues : chaque épisode du Dev du Vendredi ferme une issue et pose un tag git.

## Docs
- docs/ARCHITECTURE.md — schémas & flux
- docs/DECISIONS.md — journal des choix techniques
