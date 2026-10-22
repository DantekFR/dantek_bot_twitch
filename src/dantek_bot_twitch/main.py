try:
    import asyncio
    import logging
    import time

    import twitchio
    from twitchio import eventsub
    from twitchio.ext import commands

    from dantek_bot_twitch.configs.config_twitch import load_config
    from dantek_bot_twitch.modules.commandes import ChatCommands
    from dantek_bot_twitch.modules.token_store import TokenStore, refresh_twitch_token
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de démarrer l'application."
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
            force_subscribe=True
        )
        self.config = config
        self.bot_chat_token = None
        self.token_store = TokenStore()
        self._streamer_restored = False

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
        
    async def _restore_saved_tokens(self) -> None:
        now = int(time.time())
        for role in ("bot", "streamer"):
            entry = self.token_store.get(role)
            if not entry:
                continue
            access_token = entry.get("access_token")
            refresh_token = entry.get("refresh_token")
            if not access_token:
                LOGGER.warning("Token %s sans access_token, ignore.", role)
                continue
            
            expires_at = entry.get("expires_at")
            needs_refresh = True
            if expires_at:
                try:
                    if int(expires_at) > now + 300:
                        needs_refresh = False
                except Exception:
                    needs_refresh = True
            if needs_refresh and refresh_token:
                try:
                    new = await refresh_twitch_token(
                        str(self.config.twitch_client_id),
                        str(self.config.twitch_client_secret),
                        str(refresh_token),
                    )
                    access_token = new.get("access_token", access_token)
                    refresh_token = new.get("refresh_token", refresh_token)
                    self.token_store.set_token(
                        role=role,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=new.get("expires_in"),
                        scopes=new.get("scopes"),
                        user_id=entry.get("user_id"),
                    )
                    LOGGER.info("Token %s rafraichi.", role)
                except Exception as e:
                    LOGGER.warning("Refresh token %s impossible : %s", role, e)

            try:
                await self.add_token(access_token, refresh_token)
                if role == "bot":
                    self.bot_chat_token = access_token
                    LOGGER.info("Token bot restauré depuis data/tokens.json.")
                else:
                    self._streamer_restored = True
                    LOGGER.info("Token streamer restaure depuis data/tokens.json.")
            except Exception as e:
                LOGGER.warning("Injection token %s échouée : %s", role, e)

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
                LOGGER.info("Abonné au chat de %s", broadcaster)
            if any(_already_exists(e) for e in errors):
                LOGGER.info("Souscription chat déjà active (409), rien à faire.")
            else:
                LOGGER.warning("Echec souscription chat : %s", errors)
                
        except Exception as e:
            if _already_exists(e):
                LOGGER.info("Souscription chat déjà active (409), rien à faire.")
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
            user_id=payload.user_id or None,
        )
        try:
            await self.add_token(payload.access_token, payload.refresh_token)
        except Exception as e:
            LOGGER.error("add_token %s échoué : %s", role, e)

        if is_bot:
            self.bot_chat_token = payload.access_token
            LOGGER.info("Token du bot ajouté et persiste.")
            return
        
        self._streamer_restored = True
        LOGGER.info("Token streamer ajouté et persiste.")
        await self._subscribe_chat(payload_user_id)

    async def event_ready(self) -> None:
        LOGGER.info("[OK] Autobot prêt.")

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
