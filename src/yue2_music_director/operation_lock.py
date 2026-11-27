"""Durable local mutex ownership and explicitly inspected stale recovery.

The marker remains exclusive. A dead owner does not authorize replay of any
native/provider journal. Legacy empty markers and unknown owners are never
removed automatically or by this recovery path.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def process_birth(pid):
    """Read process creation identity without signalling or terminating it."""
    if type(pid) is not int or not 0<pid<2**32:
        return "unknown",None
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes as w
        k=ctypes.WinDLL("kernel32",use_last_error=True)
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]
        k.OpenProcess.restype=w.HANDLE
        k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
        k.GetProcessTimes.restype=w.BOOL
        k.CloseHandle.argtypes=[w.HANDLE]
        k.CloseHandle.restype=w.BOOL
        handle=k.OpenProcess(0x1000,False,pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ("absent",None) if ctypes.get_last_error()==87 else ("unknown",None)
        try:
            created,exited,kernel,user=(w.FILETIME() for _ in range(4))
            if not k.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(exited),
                                     ctypes.byref(kernel),ctypes.byref(user)):
                return "unknown",None
            birth=str((created.dwHighDateTime<<32)|created.dwLowDateTime)
            return ("absent" if exited.dwHighDateTime or exited.dwLowDateTime else "present"),birth
        finally:
            k.CloseHandle(handle)
    # Linux boot ID + /proc start ticks prevents PID reuse and reboot aliases.
    try:
        boot=Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError:
        return "unknown",None
    try:
        stat=Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except FileNotFoundError:
        return "absent",None
    except OSError:
        return "unknown",None
    try:
        fields=stat[stat.rindex(")")+2:].split()
        birth=boot+":"+fields[19]
        return ("absent" if fields[0]=="Z" else "present"),birth
    except (IndexError,ValueError):
        return "unknown",None


def _encode(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2).encode("utf-8")


def _exclusive(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def lock(path,*,context=None):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    state,birth=process_birth(os.getpid())
    owner={"schema":"operation-lock-v1","pid":os.getpid(),"process_birth":birth if state=="present" else None,
           "host":socket.gethostname(),"token":uuid.uuid4().hex,"created_utc":now(),"context":context}
    raw=_encode(owner)
    _exclusive(path,raw)
    try:
        yield
    finally:
        # A cooperating owner may remove only its own exact marker.
        if not path.is_file() or path.is_symlink() or path.read_bytes()!=raw:
            raise ValueError("Lock ownership changed; preserve the current marker")
        path.unlink()


def inspect(path):
    path=Path(path)
    if not path.exists() and not path.is_symlink():
        return {"status":"absent"}
    if path.is_symlink() or not path.is_file() or path.stat().st_size>16384:
        return {"status":"unverified","reason":"Unexpected marker type or size"}
    raw=path.read_bytes()
    result={"status":"unverified","marker_sha256":hashlib.sha256(raw).hexdigest()}
    try:
        owner=json.loads(raw)
    except (ValueError,UnicodeError):
        return {**result,"reason":"Legacy or malformed marker; no safe owner identity"}
    fields={"schema","pid","process_birth","host","token","created_utc","context"}
    if (not isinstance(owner,dict) or set(owner)!=fields or owner.get("schema")!="operation-lock-v1"
            or not isinstance(owner.get("process_birth"),str) or not owner["process_birth"]
            or not isinstance(owner.get("token"),str) or len(owner["token"])!=32
            or owner.get("host")!=socket.gethostname()):
        return {**result,"reason":"Unknown owner/process identity"}
    result["owner"]=owner
    state,birth=process_birth(owner["pid"])
    if state=="present" and birth==owner["process_birth"]:
        result["status"]="active_owner"
    elif state=="absent" or state=="present" and birth!=owner["process_birth"]:
        result["status"]="stale_owner"
    else:
        result["reason"]="Could not independently inspect process identity"
    return result


@contextmanager
def _recovery_guard(path):
    """Serialize explicit recoveries; OS releases this guard on process exit."""
    guard=path.with_name(path.name+".recovery-guard")
    if guard.is_symlink():
        raise ValueError("Unexpected recovery guard symlink")
    fd=os.open(guard,os.O_RDWR|os.O_CREAT,0o600)
    try:
        if os.fstat(fd).st_size==0:
            os.write(fd,b"0")
        os.lseek(fd,0,os.SEEK_SET)
        if os.name=="nt":
            import msvcrt
            msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def recover(path,expected_sha,receipt_base,*,confirm=False,journal_summary=None):
    """Explicit recovery of an independently verified dead owner, never replay."""
    if not confirm:
        raise ValueError("Explicit lock recovery confirmation required")
    path=Path(path)
    with _recovery_guard(path):
        evidence=inspect(path)
        if evidence.get("status")!="stale_owner" or evidence.get("marker_sha256")!=expected_sha:
            raise ValueError("Marker is not the exact inspected stale owner")
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected_sha:
            raise ValueError("Marker changed during recovery")
        receipt=Path(receipt_base)/uuid.uuid4().hex
        receipt.mkdir(parents=True,exist_ok=False)
        _exclusive(receipt/"original-marker.json",raw)
        _exclusive(receipt/"attempt.json",_encode({"schema":"lock-recovery-v1","lock_name":path.name,
                   "marker_sha256":expected_sha,"owner":evidence["owner"],"attempted_utc":now(),
                   "journal_summary":journal_summary,"journal_replay_authorized":False}))
        if inspect(path)!=evidence:
            raise ValueError("Marker changed or owner no longer verified; preserve evidence")
        path.unlink()
        _exclusive(receipt/"completed.json",_encode({"removed_utc":now(),"journal_replay_authorized":False}))
        return receipt
