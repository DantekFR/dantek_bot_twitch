try:
    import os
    from dataclasses import dataclass

    from dotenv import load_dotenv
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RunTimeError(
        "Impossible de démarrer l'application."
    )

@dataclass(frozen=True)
class Config:
    twitch_client_id: str
    twitch_token: str
    twitch_channel: str
    bot_nick: str
    ollama_url: str
    ollama_model: str

def load_config() -> Config:
    load_dotenv()

    required = ["TWITCH_CLIENT_ID", "TWITCH_TOKEN", "TWITCH_CHANNEL", "BOT_NICK"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise SystemExit(f" .env incomplet : {', '.join(missing)}")

    return Config(
        twitch_client_id=os.environ["TWITCH_CLIENT_ID"],
        twitch_token=os.environ["TWITCH_TOKEN"],
        twitch_channel=os.environ["TWITCH_CHANNEL"],
        bot_nick=os.environ["BOT_NICK"],
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-q4_K_M")
    )