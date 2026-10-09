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
    twitch_client_secret: str
    bot_id: str
    owner_id: str
    twitch_channel: str
    ollama_url: str
    ollama_model: str

def load_config() -> Config:
    load_dotenv()

    required = ["TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "BOT_ID", "OWNER_ID", "TWITCH_CHANNEL"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise SystemExit(f" .env incomplet : {', '.join(missing)}")

    return Config(
        twitch_client_id=os.environ["TWITCH_CLIENT_ID"],
        twitch_client_secret=os.environ["TWITCH_CLIENT_SECRET"],
        bot_id=os.environ["BOT_ID"],
        owner_id=os.environ["OWNER_ID"],
        twitch_channel=os.environ["TWITCH_CHANNEL"],
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-q4_K_M"),
    )