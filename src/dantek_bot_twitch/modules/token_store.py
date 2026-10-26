from __future__ import annotations
try:
    
    import json
    import os
    import time
    from pathlib import Path
    from typing import Any
    import aiohttp
except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de démarrer l'application."
    )

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TOKEN_PATH = ROOT / "data" / "tokens.json"

class TokenStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_TOKEN_PATH
        self.data : dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.data = {}
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = loaded if isinstance(loaded, dict) else {}
        except Exception:
            self.data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf_8")
        try:
            os.chmod(tmp, 0o600)
        except Exception:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except Exception:
            pass

    def get(self, role: str) -> dict[str, Any] | None:
        return self.data.get(role)

    def set_token(
        self,
        role: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | str | None = None,
        scopes: Any | None = None,
        user_id: Any | None = None,
    ) -> None:
        if not access_token:
            return

        entry = dict(self.data.get(role, {}))
        entry["access_token"] = access_token
        if refresh_token:
            entry["refresh_token"] = refresh_token
        entry.setdefault("refresh_token", None)
        now = int(time.time())
        entry["updated_at"] = now
        if expires_in is not None:
            try:
                entry["expires_at"] = now + int(expires_in)
            except Exception:
                entry["expires_at"] = now + 10800
        else:
            entry.setdefault("expires_at", now + 10800)
        if scopes is not None:
            try:
                entry["scopes"] = list(scopes)
            except Exception:
                entry["scopes"] = str(scopes)
        if user_id is not None:
            entry["user_id"] = str(user_id)
        self.data[role] = entry
        self.save()

def _scrub(body:dict) -> dict:
    out = dict(body)
    for k in ("access_token", "refresh_token", "client_secret"):
        if k in out:
            out[k] = "[REDACTED]"
    return out

async def refresh_twitch_token(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    if not refresh_token:
        raise RuntimeError("refresh_token vide : impossible de rafraichir, OAuth requise")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id" : client_id,
                "client_secret": client_secret,
                "grant-type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            try:
                body = await resp.json()
            except Exception:
                body = {}
            if resp.status != 200:
                raise RuntimeError(f"Twitch refresh HTTP {resp.status} body={_scrub(body)}")
            return body

async def validate_twitch_token(access_token: str) -> tuple[str, dict] | None:
    if not access_token:
        return ("invalid", None)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://id.twitch.tv/oauth2/validate",
                header={"Authorization": f"Bearer {access_token}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    return ("valid", await resp.json())
                if resp.status == 401:
                    return ("invalid", None)
                return ("error", None)
    except Exception:
        return ("error", None)