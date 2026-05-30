from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "server-19093.out.log"
ERR = ROOT / "server-19093.err.log"
PID = ROOT / "server.pid"


def main() -> None:
    env = os.environ.copy()
    env.setdefault("TUSHARE_RECENT_DAYS", "250")
    env.setdefault("TUSHARE_CYCLE_DAYS", "23")

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    with OUT.open("ab") as out, ERR.open("ab") as err:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "19093",
            ],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            close_fds=True,
            creationflags=creationflags,
        )
    PID.write_text(str(process.pid), encoding="utf-8")
    print(process.pid)


if __name__ == "__main__":
    main()
