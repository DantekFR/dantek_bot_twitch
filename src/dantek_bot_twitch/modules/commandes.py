try:
    import logging

    import twitchio
    from twitchio.ext import commands
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de démarrer l'application."
    )

LOGGER = logging.getLogger("Commands")

class ChatCommands(commands.Component):
    def __init__(self, bot: commands.AutoBot) -> None:
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[CHAT] {payload.chatter.name}: {payload.text}")

    @commands.command(name="test")
    async def cmd_test(self, ctx: commands.Context) -> None:
        await ctx.reply(f"{ctx.chatter.name} : le bot entend le chat!")

    @commands.command(name="discord")
    async def cmd_discord(self, ctx: commands.Context) -> None:
        await ctx.reply("Voici l'adresse du Discord : discord.gg/KEPpFSEMFY")

    @commands.command(name="love")
    async def cmd_love(self, ctx: commands.Context) -> None:
        await ctx.reply(
            "dantekfLove Derrière chaque grand streamer se cache une femme exceptionnelle… qui attend toujours qu'il éteigne son PC. dantekfLOL"
        )