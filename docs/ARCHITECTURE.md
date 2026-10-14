# Architecture

## Schéma
Viewers → Twitch Chat → EventSub (WebSocket) → AutoBot (Steam Deck)
AutoBot → Helix Send Chat Message → Twitch Chat
AutoBot → mini-serveur OAuth local (:4343) → navigateurs (autorisations)
AutoBot → modules : commands / moderation / vram / memo (Ollama local)
AutoBot → SQLite (data/, jamais committé)

## Authentification (OAuth 2.0)
- App détenue par le compte streamer (OWNER_ID)
- Le compte bot (BOT_ID) autorise : user:read:chat user:write:chat user:bot
- Le streamer autorise : channel:bot → déclenche ChatMessageSubscription
- Tokens en mémoire (v0.2) ; persistance SQLite = prochain épisode

## Réception du chat
- twitchio 3 : EventSub Chat (pas d'IRC)
- event_message (ChatMessage) dans ChatComponent
- Commandes : prefix "!", routage via commands.Component

## Hébergement & dev
- Steam Deck (SteamOS immuable) : uv en user-space, CPython managé par uv
- Dev : VS Code Remote-SSH ; tunnel du port 4343 (ssh -L 4343:localhost:4343)
- Lancement : uv run python -m dantek_bot_twitch.main (service systemd à venir)

## Sécurité & privacy
- Secrets dans .env (gitignoré) ; contrat public = .env.example
- Données viewers : SQLite local uniquement (data/), jamais sur GitHub
- Scopes minimaux ; token bot ≠ token streamer
