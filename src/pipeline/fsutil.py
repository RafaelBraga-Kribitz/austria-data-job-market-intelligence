"""Atomic file helpers that survive short Windows locks (virus scanner, indexer, a reader holding the target open).

`replace_retry` is `os.replace` with a bounded retry on PermissionError (WinError 5 access denied, WinError 32 sharing
violation). `atomic_write_text` writes a sibling `.tmp` file and replaces the target with it, so a crash or a reader never sees
a half-written file. Standard library only (public tree: src/pipeline is exported).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

REPLACE_TRIES = 8                      # waits 0.05 s * 2**i between tries: about 6.4 s in total


def replace_retry(src: Path | str, dst: Path | str, tries: int = REPLACE_TRIES) -> None:
    """os.replace(src, dst); retry on PermissionError, then re-raise it with a hint about the program that holds the file."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:
            if i == tries - 1:
                raise PermissionError(e.errno, f"{dst} is locked by another program (close Excel / Power BI / the editor): {e.strerror or e}",
                                      e.filename) from e
            time.sleep(0.05 * 2 ** i)


def atomic_write_text(path: Path | str, text: str, encoding: str = "utf-8", newline: str | None = "") -> None:
    """Write `text` to `path` via a `.tmp` sibling and replace_retry. Creates missing parent folders. newline="" keeps the text as is."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline=newline) as f:
            f.write(text)
        replace_retry(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)                  # no stray .tmp after a failed write or replace
        raise
