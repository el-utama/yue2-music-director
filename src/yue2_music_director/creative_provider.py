"""Bounded, explicitly configured OpenAI-compatible text provider."""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROLES = ("composer", "lyricist", "reviewer", "director")
ENV_NAMES = ("MUSIC_LLM_URL", "MUSIC_LLM_KEY", "MUSIC_LLM_MODEL", *("MUSIC_LLM_"+r.upper()+"_MODEL" for r in ROLES))


def configuration_source():
    return "environment" if any(name in os.environ for name in ENV_NAMES) else "local Windows configuration"


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Non-finite JSON value")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Provider redirect refused")


class TextProvider:
    def __init__(self, url, key, models):
        p = urlsplit(url)
        if (p.scheme != "https" or not p.hostname or p.username or p.password
                or p.query or p.fragment or not p.path.endswith("/chat/completions")):
            raise ValueError("Configure an HTTPS chat/completions URL")
        if not key or any(c in key for c in "\r\n"):
            raise ValueError("Missing or invalid provider key")
        if set(models) != set(ROLES) or any(not isinstance(v, str) or not v.strip()
                                          or len(v)>200 for v in models.values()):
            raise ValueError("Configure models for each role")
        self.url, self._key, self.models = url, key, dict(models)

    @classmethod
    def from_env(cls):
        default = os.environ.get("MUSIC_LLM_MODEL", "")
        return cls(os.environ.get("MUSIC_LLM_URL", ""), os.environ.get("MUSIC_LLM_KEY", ""),
                   {r: os.environ.get("MUSIC_LLM_"+r.upper()+"_MODEL", default) for r in ROLES})

    @classmethod
    def for_repo(cls, repo):
        if configuration_source()=="environment":
            # Never mix credentials from different configuration sources.
            return cls.from_env()
        from .provider_setup import load
        return load(repo)

    def identity(self):
        return {"url":self.url, "models":dict(self.models)}

    def complete(self, role, prompt, data):
        body = {"model":self.models[role], "messages":[{"role":"system","content":prompt},
                {"role":"user","content":json.dumps(data, ensure_ascii=False)}],
                "max_tokens":4096,"stream":False}
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                  headers={"Authorization":"Bearer "+self._key,"Content-Type":"application/json"},
                  method="POST")
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as response:
                raw=response.read(262145)
            if len(raw)>262144:
                raise ValueError("Oversize response")
            choice=strict_json(raw.decode("utf-8"))["choices"][0]
            if choice.get("finish_reason")!="stop":
                raise ValueError("Incomplete response")
            content=choice["message"]["content"]
            if not isinstance(content,str):
                raise ValueError("Missing final text")
            text=content.strip()
            if text.startswith("```json\n") and text.endswith("\n```"):
                text=text[len("```json\n"):-len("\n```")]
            return strict_json(text)
        except urllib.error.HTTPError as exc:
            advice={401:"authentication rejected; verify the key belongs to this provider, is complete and not expired or revoked",
                    403:"access forbidden; check key permissions, account and model access",
                    429:"rate limit or quota; do not switch to a paid model automatically"}
            raise ValueError("Provider HTTP status "+str(exc.code)+
                             ("; "+advice[exc.code] if exc.code in advice else "")) from None
        except (OSError,ValueError,KeyError,IndexError,TypeError):
            raise ValueError("Provider connection or completion failed; inspect configured provider") from None
