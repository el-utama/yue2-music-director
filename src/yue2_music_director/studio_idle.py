"""Bounded read-only Studio handoff barrier, not a GPU-memory guarantee."""
import time

from .mcp import unpack
from .native_recognition import _busy_keys


def wait_for_idle(client, stage, *, max_seconds=600, settle_seconds=5,
                  stable_samples=3, clock=time.monotonic, sleep=time.sleep):
    """Require consecutive idle observations; wait natively while busy.

    Only the existing conservative busy-state policy can clear a stage.
    Native wait's done flag alone cannot authorize the next operation.
    No mutations, retries of inference, cancellation or engine changes.
    The deadline limits scheduling additional calls, not in-flight RPC time.
    """
    if (max_seconds<=0 or settle_seconds<=0 or type(stable_samples) is not int
            or stable_samples<2):
        raise ValueError("Invalid idle barrier budget")
    deadline=clock()+max_seconds
    consecutive=0
    print("Studio idle barrier:",stage,flush=True)
    while clock()<deadline:
        status=unpack(client.call("studio_status",{}))
        if clock()>=deadline:
            break
        busy=_busy_keys(status)
        if busy:
            consecutive=0
            print("Waiting for Studio:",", ".join(busy),flush=True)
            remaining=deadline-clock()
            if remaining<2:
                break
            result=unpack(client.call("studio_wait",{"until":"idle","seconds":min(30,int(remaining))}))
            if not isinstance(result,dict) or type(result.get("done")) is not bool:
                raise ValueError("Unrecognized native idle wait response")
            # Some native terminal states are deliberately stricter in our
            # policy. Avoid a tight loop when native wait returns immediately.
            if clock()<deadline:
                sleep(min(settle_seconds,deadline-clock()))
        else:
            consecutive+=1
            if consecutive>=stable_samples:
                print("Studio stable idle:",stage,flush=True)
                return status
            sleep(min(settle_seconds,deadline-clock()))
    raise ValueError("Studio did not reach stable idle before "+stage+"; no next operation submitted")


def assert_idle(client):
    status=unpack(client.call("studio_status",{}))
    busy=_busy_keys(status)
    if busy:
        raise ValueError("Studio became busy before submission: "+", ".join(busy))
    return status
