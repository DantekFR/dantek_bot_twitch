try:
    import asyncio
    import logging

    import twitchio
    from twitchio import eventsub
    from twitchio.ext import commands

    from dantek_bot_twitch.configs.config_twitch import load_config
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RunTimeError(
        "Impossible de démarrer l'application."
    )

LOGGER = logging.getLogger("Bot")

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

    async def setup_hook(self) -> None:
        await self.add_component(ChatComponent(self))

    async def event_oauth_authorized(self, payload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)
        if not payload.user_id or payload.user_id == self.bot_id:
            LOGGER.info("Token du bot ajouté.")
            return
        subs = [eventsub.ChatMessageSubscription(
            broadcaster_user_id=payload.user_id, user_id=self.bot_id
        )]
        resp = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Echec souscription : %s", resp.errors)
        else:
            LOGGER.info("Abonné au chat de %s", payload.user_id)

    async def event_ready(self) -> None:
        LOGGER.info("[OK] AutoBot prêt.")

class ChatComponent(commands.Component):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[CHAT] {payload.chatter.name}: {payload.text}")

    @commands.command(name="test")
    async def cmd_test(self, ctx: commands.Context) -> None:
        await ctx.reply(f"{ctx.chatter.name} : le bot entend le chat!")

    @commands.command(name="discord")
    async def cmd_discord(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Voici l'adresse du Discord : discord.gg/KEPpFSEMFY")

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
