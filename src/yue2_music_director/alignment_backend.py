"""Discover optional mVocalToolkit models without submitting or installing anything."""
import http.client
import json
from urllib.parse import urlsplit
from pathlib import Path

from .native_recognition import _write
from .multilingual_fidelity import SUPPORTED

MAX_RESPONSE=2*1024*1024
MODEL="hubertfa-zh-ja-en-v0.0.7"


def endpoint(url):
    u=urlsplit(url)
    if (u.scheme!="http" or u.hostname not in ("127.0.0.1","::1","localhost")
            or u.username is not None or u.password is not None
            or u.path not in ("","/") or u.query or u.fragment or not u.port):
        raise ValueError("Explicit loopback HTTP base URL with port required")
    return u.hostname,u.port


def get_json(host,port,path):
    # No proxy, redirection or network access to remote hosts.
    conn=http.client.HTTPConnection(host,port,timeout=5)
    try:
        conn.request("GET",path,headers={"Accept":"application/json"})
        response=conn.getresponse()
        if response.status!=200:
            raise ValueError("Alignment discovery returned HTTP "+str(response.status))
        payload=response.read(MAX_RESPONSE+1)
        if len(payload)>MAX_RESPONSE:
            raise ValueError("Alignment discovery response exceeds limit")
        data=json.loads(payload)
        if not isinstance(data,dict):
            raise ValueError("Unexpected discovery response")
        return data
    finally:
        conn.close()


def preflight(language,out,url="http://127.0.0.1:8765"):
    if language not in SUPPORTED:
        raise ValueError("Unsupported director scoring language")
    out=Path(out).resolve()
    if out.exists():
        raise ValueError("Fresh alignment discovery report required")
    host,port=endpoint(url)
    report={"schema":"alignment-backend-preflight-v1","language":language,"status":"backend_unavailable",
            "models":[],"preferred_research_model":MODEL if language in ("zh","ja","en") else None,
            "alignment_calls":0,"recognition_calls":0,"audio_jobs_created":0,
            "downloads_requested":0,"correction_allowed":False,"phonetic_alignment_verified":False,
            "warnings":["Catalog language availability and installation are not accuracy or license verification.",
                        "Discovery is read-only; no model/engine installation or alignment job.",
                        "A forced alignment assumes the supplied sequence; it does not verify sung pronunciation.",
                        "A running external toolkit may have its own update and catalog behavior. Disable auto-update and review external network settings separately."]}
    try:
        health=get_json(host,port,"/health")
        catalog=get_json(host,port,"/languages?task=align")
        if catalog.get("task")!="align" or not isinstance(catalog.get("languages"),list):
            raise ValueError("Unrecognized alignment catalog")
        if not isinstance(health.get("version"),str):
            raise ValueError("Toolkit health version unavailable")
        report["backend_version"]=health["version"]
        seen=set()
        for entry in catalog["languages"]:
            if not isinstance(entry,dict):
                raise ValueError("Invalid catalog language entry")
            if entry.get("code")!=language:
                continue
            if not isinstance(entry.get("models"),list):
                raise ValueError("Missing language-specific models")
            for row in entry["models"]:
                if (not isinstance(row,dict) or not isinstance(row.get("id"),str)
                        or not row["id"] or not isinstance(row.get("engine"),str)
                        or type(row.get("installed")) is not bool or row["id"] in seen):
                    raise ValueError("Unrecognized or duplicate model record")
                seen.add(row["id"])
                report["models"].append({"id":row["id"],"engine":row["engine"],
                                          "installed":row["installed"]})
        report["status"]="installed_models_require_validation" if any(m["installed"] for m in report["models"]) else (
            "model_installation_required" if report["models"] else "language_model_unavailable")
    except (OSError,ValueError,TypeError,http.client.HTTPException) as exc:
        report["status"]="backend_unavailable"
        report["models"]=[]
        report["reason"]=str(exc)
    out.parent.mkdir(parents=True,exist_ok=True)
    _write(out,report)
    return report
