import logging
import aiohttp

LOGGER = logging.getLogger("AI")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:7b-instruct-q4_K_M"

BASE_SYSTEM = """Tu es dantekos_bo, un membre de la communauté de la chaine Twitch DanTekFR.
Tu parles en français, naturellement, comme un viewer qui connait bien le streamer.
Réponse courte : 200 caractères max. Pas de "en étant qu'IA". Pas de préambule.

FAITS SUR LA CHAINE (à respecter, c'est ton univers) :
{facts}

MEMOIRE DU VIEWER QUI TE PARLE :
{memory}

CONVERSATION RECENTE AVEC CE VIEWER :
{history}"""

async def ask_ai(question: str, fact: str, memory: str, history: list[str]) -> str:
    system = BASE_SYSTEM.format(
        facts=facts or "(aucun fait renseigné)",
        memory=memory or "(je ne te connais pas encore)",
        history="\n".join(history) if history else "(premier échange)",
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content" : system},
                        {"role": "user", "content": question},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 120},
                },
                timeout=aiohttp.ClientTimeout(total=40),
            )as resp:
                if resp.status != 200:
                    return "Je suis en pause café, reviens plus tard"
                data = await resp.json()
                ans = data.get("response", "").strip()
                return ans[:450] + "..." if len(ans) > 450 else ans or "..."
    except Exception as exc:
        LOGGER.error("Ollama injoignable : %s", exc)
        return "J'ai bugué, réessaie"