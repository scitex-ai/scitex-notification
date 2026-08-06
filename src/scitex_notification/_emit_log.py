"""Append-only audit log of every notification emission, naming its caller.

WHY THIS EXISTS (incident, 2026-08-06)
--------------------------------------
The operator was receiving real PHONE CALLS and could not tell what was placing
them: 「どのエージェントかプログラムかわかんないんですけど、電話をかけてくれてる」.
Neither could I. By the time anyone looked, the calling process had died in a
restart and there was no record anywhere — so the question "who called me?" was
not merely unanswered, it was UNANSWERABLE. That is a missing facility, not a
failed investigation.

Their instruction: 「サイテックスノーティフィケーションは全部ホームのほうの
ローカルステートにランタイムにログを入れておいてもらえるとうれしいです。
特に電話の場合めんどくさいんでどこから来てるかわかんないと」.

TWO DESIGN POINTS THAT ARE NOT NEGOTIABLE
-----------------------------------------
1. The ATTEMPT is logged BEFORE the backend is invoked, not after. A call that
   crashes or hangs mid-dial still costs money and must still be attributable;
   an after-the-fact log would miss exactly the cases worth investigating.
2. Logging NEVER raises. A notification is often itself an error path — if the
   audit log could break it, a full disk would silence the alerts you most need.
   Every failure here is swallowed deliberately.

The record answers "who", because that is the question that was unanswerable:
pid/ppid/argv of the calling process, the agent id if one is set, cwd and user.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

#: Body text is truncated — the log is for attribution, not message archival.
_MAX_BODY = 400


def log_path() -> Path:
    """Where emissions are recorded.

    Sits beside the package's existing config root (~/.scitex/notification/),
    under runtime/ per the fleet convention that runtime/ holds regenerable
    local state.
    """
    override = os.getenv("SCITEX_NOTIFICATION_RUNTIME_LOG")
    if override:
        return Path(override).expanduser()
    root = os.getenv("SCITEX_DIR") or os.path.join(Path.home(), ".scitex")
    return Path(root).expanduser() / "notification" / "runtime" / "emissions.jsonl"


def _caller() -> dict:
    """Identify the process asking for this notification."""
    info: dict[str, Any] = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "user": os.getenv("USER") or os.getenv("LOGNAME") or "",
        "cwd": os.getcwd(),
    }
    # Agent identity, when the caller is a fleet agent. Several names are in
    # use across the fleet; record whichever is set rather than guessing one.
    for var in (
        "SCITEX_CARDS_AGENT_ID",
        "SCITEX_TODO_AGENT_ID",
        "SAC_NAME",
        "CLAUDE_AGENT_ID",
    ):
        val = os.getenv(var)
        if val:
            info["agent"] = val
            info["agent_var"] = var
            break
    # argv of this process and its parent — the parent is usually the more
    # informative one (the cron line, the agent wrapper) when a library call
    # is buried inside a long-lived python process.
    for key, pid in (("argv", os.getpid()), ("parent_argv", os.getppid())):
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
            info[key] = raw.decode("utf-8", "replace").replace("\0", " ").strip()[:300]
        except Exception:  # stx-allow: fallback (reason: /proc is absent on macOS and unreadable for a foreign pid; a missing argv must not stop the record being written)
            pass
    return info


def record(
    *,
    phase: str,
    backend: str,
    level: str = "",
    title: Optional[str] = None,
    message: str = "",
    ok: Optional[bool] = None,
    error: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Append one JSONL record. Never raises.

    phase is ``attempt`` (written before the backend runs) or ``result``.
    A lone ``attempt`` with no matching ``result`` is itself the signal that
    something died mid-send — which is precisely the case worth seeing.
    """
    try:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "phase": phase,
            "backend": str(backend),
            # str() on purpose: callers pass a NotifyLevel ENUM here, which
            # json.dumps refuses. Caught only because the swallow below turned
            # the TypeError into a silently EMPTY log file -- the exact "reports
            # success, does nothing" shape this module exists to expose. Coerce
            # everything that crosses into JSON rather than trusting the type.
            "level": str(level),
            "title": str(title or ""),
            "message": (message or "")[:_MAX_BODY],
            "caller": _caller(),
        }
        if ok is not None:
            entry["ok"] = ok
        if error:
            entry["error"] = str(error)[:300]
        if extra:
            entry["extra"] = extra

        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # stx-allow: fallback (reason: the audit log must never break a notification -- notifications are themselves an error path, and a full disk here would silence the alerts that matter most)
        pass
