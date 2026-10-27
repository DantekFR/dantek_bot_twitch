try:
    import asyncio
    import logging
    import time

    import twitchio
    from twitchio import eventsub
    from twitchio.ext import commands

    from dantek_bot_twitch.configs.config_twitch import load_config
    from dantek_bot_twitch.modules.commandes import ChatCommands
    from dantek_bot_twitch.modules.token_store import TokenStore, refresh_twitch_token, validate_twitch_token
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de demarrer l'application."
    )

LOGGER = logging.getLogger("Bot")

try:
    from dantek_bot_twitch.modules.storage import Database
    _STORAGE_IMPORT_OK = True
except Exception as e:
    Database = None
    _STORAGE_IMPORT_OK = False
    print(f"[WARN] Import storage échoué ({e}), mémoire désactivée.")


def _already_exists(err) -> bool:
    s = str(err)
    if "already exists" in s or "409" in s:
        return True
    inner = getattr(err, "error", None)
    if inner is not None:
        si = str(inner)
        if "already exists" in si or "409" in si:
            return True
    return False


class Bot(commands.AutoBot):
    def __init__(self, config) -> None:
        super().__init__(
            client_id=config.twitch_client_id,
            client_secret=config.twitch_client_secret,
            bot_id=config.bot_id,
            owner_id=config.owner_id,
            prefix="!",
            force_subscribe=True,
        )
        self.config = config
        self.bot_chat_token = None
        self.token_store = TokenStore()
        self._streamer_restored = False
        self._refresh_task = None
        self._oauth_required: set[str] = set()
        self._token_fail_cooldown: dict[str, int] = {}

        self.storage = None
        if _STORAGE_IMPORT_OK:
            try:
                self.storage = Database()
                LOGGER.info("Mémoire activée : %s", self.storage.path)
            except Exception as e:
                LOGGER.warning("Init storage échouée (%s), mémoire désactivée.", e)
                self.storage = None

    async def setup_hook(self) -> None:
        await self._restore_saved_tokens()
        await self.add_component(ChatCommands(self))
        if self._streamer_restored:
            await self._subscribe_chat(str(getattr(self.config, "owner_id", "") or ""))
        self._refresh_task = asyncio.create_task(self._token_refresh_loop())

    def _mark_oauth_required(self, role: str, reason: str) -> None:
        self._oauth_required.add(role)
        self._token_fail_cooldown[role] = int(time.time())
        if role == "bot":
            self.bot_chat_token = None
        LOGGER.error("OAuth requise pour %s : %s", role, reason)

    async def _inject(self, role: str, access_token: str, refresh_token: str) -> bool:
        try:
            await self.add_token(access_token, refresh_token)
        except Exception as e:
            self._mark_oauth_required(role, f"add_token échoué : {e}")
            return False

        if role == "bot":
            self.bot_chat_token = access_token
        else:
            self._streamer_restored = True
        
        self._oauth_required.discard(role)
        self._token_fail_cooldown.pop(role, None)
        return True

    async def force_refresh_now(self, role: str) -> None:
        entry = self.token_store.get(role)
        if not entry:
            self._mark_oauth_required(role, "force_refresh : pas de token stocké")
            return
        
        refresh_token = entry.get("refresh_token")
        if not refresh_token:
            self._mark_oauth_required(role, "force_refresh : refresh absent")
            return
        
        try:
            new = await refresh_twitch_token(
                str(self.config.twitch_client_id),
                str(self.config.twitch_client_secret),
                str(refresh_token),
            )
        except Exception as e:
            self._mark_oauth_required(role, f"force_refresh échoué : {e}")
            return
        
        new_access = new.get("access_token")
        new_refresh = new.get("refresh_token", refresh_token)
        if not new_access:
            self._mark_oauth_required(role, "force_refresh sans access_token")
            return
        self.token_store.set_token(
            role=role,
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=new.get("expires_in"),
            scopes=new.get("scope") or new.get("scopes"),
            user_id=entry.get("user_id"),
        )
        await self._inject(role, new_access, new_refresh)
        LOGGER.info("Token %s rafraichi par force_refresh (Helix 401).", role)

    async def _restore_saved_tokens(self) -> None:
        for role in ("bot", "streamer"):
            entry = self.token_store.get(role)
            if not entry:
                self._mark_oauth_required(role, "aucun token stocké")
                continue
            access_token = entry.get("access_token")
            refresh_token = entry.get("refresh_token")
            if not access_token or not refresh_token:
                self._mark_oauth_required(role, "access_token ou refresh absent dans le fichier")
                continue
                
            if await self._inject(role, access_token, refresh_token):
                LOGGER.info("Token %s injecté.", role)
              
    async def _token_refresh_loop(self) -> None:
        LOGGER.info("Loop de refresh proactif démarrée.")
        first_tick = True
        while True:
            if not first_tick:
                await asyncio.sleep(60)
            first_tick = False
            now = int(time.time())
            for role in ("bot", "streamer"):
                if role in self._oauth_required:
                    if now - self._token_fail_cooldown.get(role, 0) < 900:
                        continue
                    self._oauth_required.discard(role)

                entry = self.token_store.get(role)
                if not entry:
                    continue

                access_token = entry.get("access_token")
                refresh_token = entry.get("refresh_token")
                if not access_token:
                    self._mark_oauth_required(role, "access_token absent dans la loop")
                    continue
                
                expires_at = entry.get("expires_at")
                try:
                    remaining = int(expires_at) - now if expires_at else -1
                except Exception:
                    remaining = -1
                if remaining > 600:
                    continue

                state, data = await validate_twitch_token(access_token)
                if state == "valid":
                    self.token_store.set_token(
                        role=role,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=(data or {}).get("expires_in"),
                        scopes=(data or {}).get("scopes"),
                        user_id=(data or {}).get("user_id"),
                    )
                    await self._inject(role, access_token, refresh_token or "")
                    LOGGER.info("Token %s validé (loop), expires_at recalculé.", role)
                    continue
                if state == "error" and remaining > 0:
                    LOGGER.warning("Token %s : validate en erreur réseau, on attend le prochain tick.", role)
                    continue

                if state == "error":
                    LOGGER.warning("Token %s : validate muet et accès expiré (horloge locale) -> refresh tenté malgré tout.", role)

                if not refresh_token:
                    self._mark_oauth_required(role, "access mort et refresh absent")
                    continue

                try:
                    new = await refresh_twitch_token(
                        str(self.config.twitch_client_id),
                        str(self.config.twitch_client_secret),
                        str(refresh_token),
                    )
                except Exception as e:
                    self._mark_oauth_required(role, f"loop refresh échoué : {e}")
                    continue

                new_access = new.get("access_token")
                new_refresh = new.get("refresh_token", refresh_token)
                if not new_access:
                    self._mark_oauth_required(role, "loop refresh sans access_token")
                    continue

                self.token_store.set_token(
                    role=role,
                    access_token=new_access,
                    refresh_token=new_refresh,
                    expires_in=new.get("expires_in"),
                    scopes=new.get("scope") or new.get("scopes"),
                    user_id=entry.get("user_id"),
                )

                await self._inject(role, new_access, new_refresh)
                LOGGER.info("Token %s rafraichi par la loop proactive.", role)
                
    async def _subscribe_chat(self, broadcaster_id: str) -> None:
        bot_id = str(getattr(self, "bot_id", "") or "")
        if not broadcaster_id or not bot_id:
            LOGGER.warning("Subscription impossible : owner_id ou bot_id manquant.")
            return
        subs = [eventsub.ChatMessageSubscription(broadcaster_user_id=broadcaster_id, user_id=bot_id)]
        try:
            resp = await self.multi_subscribe(subs)
            errors = getattr(resp, "errors", None)
            if not errors:
                LOGGER.info("Abonné au chat de %s", broadcaster_id)
                return
            if any(_already_exists(e) for e in errors):
                LOGGER.info("Souscription chat déjà active (409), rien à faire.")
            else:
                LOGGER.warning("Echec souscription chat : %s", errors)
        except Exception as e:
            if _already_exists(e):
                LOGGER.info("Souscription chat deja active (409), rien a faire.")
            else:
                LOGGER.warning("Exception souscription chat : %s", e)

    async def event_oauth_authorized(self, payload) -> None:
        payload_user_id = str(getattr(payload, "user_id", "") or "")
        bot_id = str(getattr(self, "bot_id", "") or "")
        is_bot = (not payload_user_id) or (payload_user_id == bot_id)
        role = "bot" if is_bot else "streamer"

        self.token_store.set_token(
            role=role,
            access_token=payload.access_token,
            refresh_token=payload.refresh_token,
            expires_in=getattr(payload, "expires_in", None),
            scopes=getattr(payload, "scopes", None),
            user_id=payload_user_id or None,
        )

        if not await self._inject(role, payload.access_token, payload.refresh_token):
            LOGGER.error("add_token %s échoué malgré OAuth.", role)

        if is_bot:
            LOGGER.info("Token du bot ajouté et persiste.")
            return

        LOGGER.info("Token streamer ajouté et persiste.")
        await self._subscribe_chat(payload_user_id)

    async def event_ready(self) -> None:
        LOGGER.info("[OK] AutoBot pret.")


def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)
    config = load_config()

    async def runner() -> None:
        async with Bot(config) as bot:
            await bot.start(load_tokens=False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Arrêt.")


if __name__ == "__main__":
    main()
