"""Bounded, explicitly configured OpenAI-compatible text provider."""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROLES = ("composer", "lyricist", "reviewer", "director")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NEMOTRON_VL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
SMOKE_SCHEMA = {"type":"object","properties":{"ready":{"type":"boolean","enum":[True]}},
                "required":["ready"],"additionalProperties":False}


def role_schema(role):
    from . import composer, lyricist, creative_reviewer, director_decision
    return {"composer":composer.SCHEMA,"lyricist":lyricist.SCHEMA,
            "reviewer":creative_reviewer.SCHEMA,"director":director_decision.SCHEMA}[role]

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
        if (not key or not key.isascii() or any(c.isspace() or ord(c)<33 or ord(c)>126 for c in key)):
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
        identity={"url":self.url, "models":dict(self.models)}
        if self.url==NVIDIA_URL and NEMOTRON_VL in self.models.values():
            identity["nemotron_vl_policy"]="structured-v1"
        return identity

    def nvidia_catalog(self):
        """Read-only hosted NIM catalog probe; not proof of inference entitlement."""
        if self.url != "https://integrate.api.nvidia.com/v1/chat/completions":
            raise ValueError("NVIDIA catalog probe requires the exact hosted NIM endpoint")
        request=urllib.request.Request("https://integrate.api.nvidia.com/v1/models",
                  headers={"Authorization":"Bearer "+self._key,"Accept":"application/json"},
                  method="GET")
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=30) as response:
                raw=response.read(1048577)
            if len(raw)>1048576:
                raise ValueError("Catalog response too large")
            data=strict_json(raw.decode("utf-8"))["data"]
            if not isinstance(data,list) or any(not isinstance(x,dict) or
                    not isinstance(x.get("id"),str) for x in data):
                raise ValueError("Invalid catalog response")
            return 200, {x["id"] for x in data}
        except urllib.error.HTTPError as exc:
            return exc.code, set()
        except (OSError,ValueError,KeyError,TypeError):
            raise ValueError("NVIDIA catalog connection or response failed") from None

    def complete(self, role, prompt, data, *, smoke=False):
        body = {"model":self.models[role], "messages":[{"role":"system","content":prompt},
                {"role":"user","content":json.dumps(data, ensure_ascii=False)}],
                "max_tokens":4096,"stream":False}
        if self.url==NVIDIA_URL and self.models[role]==NEMOTRON_VL:
            schema=SMOKE_SCHEMA if smoke else role_schema(role)
            body["response_format"]={"type":"json_schema","json_schema":{
                "name":"provider_check" if smoke else role+"_result","strict":True,"schema":schema}}
            # Hosted model documents a 16384 default completion budget and reasoning control.
            body["max_tokens"]=256 if smoke else 16384
            body["chat_template_kwargs"]={"enable_thinking":not smoke}
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                  headers={"Authorization":"Bearer "+self._key,"Content-Type":"application/json","Accept":"application/json"},
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
            result=strict_json(text)
            if not isinstance(result,dict):
                raise ValueError("Final JSON is not an object")
            return result
        except urllib.error.HTTPError as exc:
            advice={401:"authentication rejected; verify the key belongs to this provider, is complete and not expired or revoked",
                    403:"access forbidden; check key permissions, account and model access",
                    429:"rate limit or quota; do not switch to a paid model automatically"}
            raise ValueError("Provider HTTP status "+str(exc.code)+
                             ("; "+advice[exc.code] if exc.code in advice else "")) from None
        except (OSError,ValueError,KeyError,IndexError,TypeError):
            raise ValueError("Provider connection or completion failed; inspect configured provider") from None
