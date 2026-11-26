"""Local Windows provider setup; DPAPI current-user protected key, no transcript."""
import argparse
import base64
import ctypes
from ctypes import wintypes
import getpass
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import sys
import warnings

from .creative_provider import TextProvider, ROLES, strict_json, configuration_source
from .native_draft import atomic_write

PRESETS={"1":"https://integrate.api.nvidia.com/v1/chat/completions",
         "2":"https://openrouter.ai/api/v1/chat/completions"}
NVIDIA_DEFAULT="nvidia/nemotron-3.5-super-vl-120b-a12b"


class Blob(ctypes.Structure):
    _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(data, *, decrypt=False):
    if os.name!="nt":
        raise ValueError("Windows DPAPI required; use explicit environment configuration elsewhere")
    crypt=ctypes.WinDLL("crypt32",use_last_error=True)
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),
                 ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    if not data or len(data)>65536:
        raise ValueError("Invalid protected credential size")
    buffer=ctypes.create_string_buffer(data,len(data))
    source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
    out=Blob()
    try:
        # CRYPTPROTECT_UI_FORBIDDEN, without machine-scope flag.
        if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):
            raise ValueError("Windows credential protection failed (same user required)")
        return ctypes.string_at(out.pbData,out.cbData)
    finally:
        if out.pbData:
            ctypes.memset(out.pbData,0,out.cbData)
            kernel.LocalFree(ctypes.cast(out.pbData,ctypes.c_void_p))
        ctypes.memset(buffer,0,len(data))


def location(repo):
    return repo/"local/llm-provider.json"


def save(repo, url, key, models, *, protect=dpapi):
    p=TextProvider(url,key,models)
    if len(key)>4096:
        raise ValueError("Credential too long")
    path=location(repo)
    path.parent.mkdir(parents=True,exist_ok=True)
    protected=base64.b64encode(protect(key.encode("utf-8"))).decode("ascii")
    atomic_write(path,{"schema":"music-llm-dpapi-v1","url":p.url,"models":p.models,
                       "protected_key":protected})


def load(repo, *, unprotect=dpapi):
    path=location(repo)
    if not path.is_file():
        raise ValueError("Provider not configured. Run music.cmd --setup once.")
    if path.stat().st_size>100000:
        raise ValueError("Provider configuration too large")
    record=strict_json(path.read_text(encoding="utf-8"))
    if (not isinstance(record,dict) or set(record)!={"schema","url","models","protected_key"}
            or record["schema"]!="music-llm-dpapi-v1"):
        raise ValueError("Invalid local provider configuration")
    try:
        key=unprotect(base64.b64decode(record["protected_key"],validate=True),decrypt=True).decode("utf-8")
    except (ValueError,TypeError,UnicodeError):
        raise ValueError("Cannot decrypt provider key in this Windows account; run setup") from None
    return TextProvider(record["url"],key,record["models"])


def setup(repo):
    if os.name!="nt" or not sys.stdin.isatty():
        raise ValueError("Run setup directly in the Windows terminal")
    if location(repo).exists() and input("Replace current local provider settings? [y/N]: ").strip().lower()!="y":
        print("Existing configuration retained.")
        return 0
    print("1. NVIDIA NIM API\n2. OpenRouter (explicit free model)\n3. Other HTTPS OpenAI-compatible API")
    choice=input("Provider [1/2/3]: ").strip()
    if choice not in ("1","2","3"):
        raise ValueError("Select a provider")
    url=PRESETS.get(choice) or input("Full HTTPS chat/completions URL: ").strip()
    prompt="Exact model ID from your provider"
    if choice=="1":
        prompt+=" ["+NVIDIA_DEFAULT+"]"
    model=input(prompt+": ").strip()
    if choice=="1" and not model:
        model=NVIDIA_DEFAULT
    if choice=="2" and not model.endswith(":free"):
        raise ValueError("OpenRouter preset requires an explicit :free model ID; no auto-router")
    if not model:
        raise ValueError("Model ID required")
    with warnings.catch_warnings():
        warnings.simplefilter("error",getpass.GetPassWarning)
        key=getpass.getpass("API key (hidden; stays on this PC): ").strip()
    save(repo,url,key,{r:model for r in ROLES})
    print("Saved encrypted local configuration. No API calls made.")
    if configuration_source()=="environment":
        print("WARNING: MUSIC_LLM_* environment settings override this local configuration.")
    print("The selected provider's quotas and charges apply; no paid-model fallback.")
    return 0


def check(repo):
    print("Configuration source:",configuration_source(),flush=True)
    p=TextProvider.for_repo(repo)
    print("Provider host:",urlsplit(p.url).hostname,flush=True)
    # No credential value, prefix, fingerprint, URL path or raw error body in output.
    print("Credential loaded: yes (not yet authenticated)",flush=True)
    seen=set()
    for role,model in p.models.items():
        if model in seen:
            continue
        seen.add(model)
        print("Checking role:",role,"| model:",model,flush=True)
        result=p.complete(role,'Return exactly {"ready":true} as JSON. No other text.',{"test":"connection"})
        if not isinstance(result,dict) or set(result)!={"ready"} or result["ready"] is not True:
            raise ValueError("Provider JSON smoke check failed for "+role)
        print("Provider JSON check passed for",role,flush=True)
    print("No song, ASR, MOSS or private song text used.")
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--setup",action="store_true")
    modes.add_argument("--check",action="store_true",help="Explicitly authorize synthetic provider calls")
    a=parser.parse_args()
    try:
        return setup(a.repo.resolve()) if a.setup else check(a.repo.resolve())
    except (OSError,ValueError,TypeError,KeyError,EOFError,getpass.GetPassWarning) as exc:
        # Never print input or provider secrets.
        print("ERROR: "+str(exc) if isinstance(exc,ValueError) else "ERROR: provider setup/check failed",file=sys.stderr)
        if a.check and "HTTP status" in str(exc) and ("401" in str(exc) or "403" in str(exc)):
            print("If NVIDIA NIM is selected, check the NVIDIA API key and Public API Endpoints permission at build.nvidia.com/settings/api-keys. A key from another provider cannot authenticate here.",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
