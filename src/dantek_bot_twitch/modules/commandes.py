try:
    import logging
    import re

    import twitchio
    from twitchio.ext import commands
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de démarrer l'application."
    )

LOGGER = logging.getLogger("Commands")

BOT_LOGIN = 'dantekos_bot'
_MENTION_RE = re.compile(rf"@{re.escape(BOT_LOGIN)}\b", re.IGNORECASE)

def extract_mention_question(text: str) -> str | None:
    if not _MENTION_RE.search(text):
        return None
    return _MENTION_RE.sub("", text).strip()

class ChatCommands(commands.Component):
    def __init__(self, bot: commands.AutoBot) -> None:
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        chatter = payload.chatter

        if chatter.name.lower() == BOT_LOGIN:
            return

        text = payload.text
        print(f"[CHAT] {chatter.name}: {text}")

        question = extract_mention_question(text)
        if question is not None:
            await self._handle_ai_mention(payload, question)
            return

    async def _handle_ai_mention(self, payload, question: str) -> None:
        if not question:
            await payload.channel.send(
                f"@{payload.chatter.name}: tape @dantekos_bot suivie de ta question!"
            )
            return

        vid = str(payload.chatter.id)
        storage = self.bot.storage
        try:
            await payload.channel.send_typing()
        except Exception:
            pass
        answer = await ask_ai(
            question,
            storage.facts_text(),
            storage.get_viewer_facts(vid),
            storage.recent_exchanges(vid),
        )
        storage.log_exchange(vid, payload.chatter.name, question, answer)
        await payload.channel.send(f"@{payload.chatter.name}: {answer}")

    @commands.command(name="test")
    async def cmd_test(self, ctx: commands.Context) -> None:
        await ctx.reply("le bot entend le chat!")

    @commands.command(name="discord")
    async def cmd_discord(self, ctx: commands.Context) -> None:
        await ctx.reply("Voici l'adresse du Discord : discord.gg/KEPpFSEMFY")

    @commands.command(name="love")
    async def cmd_love(self, ctx: commands.Context) -> None:
        await ctx.reply(
            "dantekfLove Derrière chaque grand streamer se cache une femme exceptionnelle… qui attend toujours qu'il éteigne son PC. dantekfLOL"
        )

    @commands.command(name="redonnelargent")
    async def cmd_redonnelargent(self, ctx: commands.Context) -> None:
        await ctx.reply("@DanTekFR ne rembourse rien il a une famille à nourrir")