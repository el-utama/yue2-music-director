"""Explicitly restore the installed stock Balanced backbone using Studio's native tool."""
import time
from .experiments import read_own_model, model_selection_label, stock_profile_checks
from .mcp import unpack
from .native_recognition import _busy_keys


def select_stock(client, tools, *, max_waits=60, sleep=time.sleep):
    if "models_own_select" not in tools:
        raise ValueError("Native model-selection tool is unavailable")
    schema=tools["models_own_select"]
    if schema.get("properties",{}).get("file",{}).get("type")!="string":
        raise ValueError("Unrecognized native model-selection contract")
    status=unpack(client.call("studio_status",{}))
    models=unpack(client.call("models_status",{}))
    own=read_own_model(client)
    if _busy_keys(status):
        raise ValueError("Studio has active work; no model change made")
    if not isinstance(models,dict):
        raise ValueError("Unrecognized models status; no model change made")
    checks=stock_profile_checks(models)
    print("Stock profile checks:",", ".join(k+"="+str(v) for k,v in checks.items()),flush=True)
    active=models.get("active")
    if isinstance(active,dict):
        print("Download receipt:",model_selection_label(active,"status"),flush=True)
    if not all(checks.values()):
        raise ValueError("Stock profile check failed: "+", ".join(k for k,ok in checks.items() if not ok)+"; no model change made")
    if ("selected" not in own or "download" not in own or own["download"] is not None
            or own.get("missing") is not False or "own_model" not in status or "own_model" not in models
            or status["own_model"]!=own["selected"] or models["own_model"]!=own["selected"]):
        raise ValueError("Model selection reads disagree or download is active; no model change made")
    selected=own["selected"]
    if selected is not None:
        if not isinstance(selected,str) or not selected.strip():
            raise ValueError("Unexpected selected model identity")
        if models.get("engine_ready") is not True or models.get("selection_matches_engine") is not True:
            raise ValueError("Current engine is not confirmed ready; no model change made")
        print("Explicit stock selection: removing override",model_selection_label(own,"selected"),flush=True)
        # Empty file is the native documented 'Do not use' selection.
        # One call only: no automatic retry, delete, download or rollback.
        client.call("models_own_select",{"file":""})
    else:
        print("Stock selection already present; no model write.",flush=True)
    for attempt in range(max_waits+1):
        own=read_own_model(client)
        models=unpack(client.call("models_status",{}))
        if (isinstance(models,dict) and "selected" in own and own["selected"] is None
                and own.get("missing") is False and "download" in own and own["download"] is None
                and "own_model" in models and models["own_model"] is None
                and models.get("selected_profile_id")=="balanced"
                and models.get("engine_ready") is True and models.get("selection_matches_engine") is True):
            print("Stock backbone selected and running engine matches.",flush=True)
            return
        if attempt<max_waits:
            if attempt%5==0:
                print("Waiting for Studio to load stock backbone...",flush=True)
            sleep(3)
    raise ValueError("Stock engine not confirmed ready within bounded wait; no song submitted")
