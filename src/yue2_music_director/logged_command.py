"""Run an explicit local command, preserving stdout/stderr for cross-device support."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def run(log, command, console=None):
    if not command:
        raise ValueError("A command is required")
    console = sys.stdout if console is None else console
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8", buffering=1) as out:
        def emit(line):
            out.write(line)
            console.write(line)
            console.flush()
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        try:
            with subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True,
                                  encoding="utf-8", errors="replace",
                                  env=env, shell=False) as child:
                try:
                    for line in child.stdout:
                        emit(line)
                    code = child.wait()
                except KeyboardInterrupt:
                    child.terminate()
                    child.wait()
                    code = 130
        except OSError as exc:
            emit(f"ERROR: {exc}\n")
            code = 2
        emit(f"\nExit code: {code}\n")
    print(f"Transcript saved: {log}", file=console, flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    return run(args.log, command)


if __name__ == "__main__":
    raise SystemExit(main())
