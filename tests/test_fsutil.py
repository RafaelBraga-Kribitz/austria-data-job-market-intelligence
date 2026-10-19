"""Atomic write helpers (src/pipeline/fsutil.py): retry on short Windows locks, no stray .tmp, no half-written target."""
from __future__ import annotations

import os

import pytest

import fsutil


def _locked(monkeypatch, fails: int):
    """os.replace that raises PermissionError `fails` times, then works. Returns the call counter."""
    real, calls = os.replace, {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] <= fails:
            raise PermissionError(13, "The process cannot access the file because it is being used by another process")
        return real(src, dst)
    monkeypatch.setattr(fsutil.os, "replace", flaky)
    monkeypatch.setattr(fsutil.time, "sleep", lambda s: None)
    return calls


def test_replace_retry_succeeds_after_two_permission_errors(tmp_path, monkeypatch):
    src, dst = tmp_path / "a.tmp", tmp_path / "a.txt"
    src.write_text("new", encoding="utf-8")
    dst.write_text("old", encoding="utf-8")
    calls = _locked(monkeypatch, 2)
    fsutil.replace_retry(src, dst)
    assert calls["n"] == 3 and dst.read_text(encoding="utf-8") == "new" and not src.exists()


def test_replace_retry_raises_after_all_tries_with_a_hint(tmp_path, monkeypatch):
    src, dst = tmp_path / "b.tmp", tmp_path / "b.txt"
    src.write_text("new", encoding="utf-8")
    calls = _locked(monkeypatch, 99)
    with pytest.raises(PermissionError, match="locked by another program"):
        fsutil.replace_retry(src, dst, tries=4)
    assert calls["n"] == 4 and src.exists()                          # source stays for the caller to deal with


def test_replace_retry_does_not_swallow_other_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        fsutil.replace_retry(tmp_path / "missing.tmp", tmp_path / "x.txt")


def test_atomic_write_text_creates_parents_and_leaves_no_tmp(tmp_path):
    target = tmp_path / "deep" / "er" / "file.csv"
    fsutil.atomic_write_text(target, "a,b\n1,2\n", newline="\n")
    assert target.read_bytes() == b"a,b\n1,2\n"
    assert [p.name for p in target.parent.iterdir()] == ["file.csv"]
    fsutil.atomic_write_text(target, "x\r\n", encoding="utf-8-sig")             # overwrite, BOM, newline="" keeps CRLF as given
    assert target.read_bytes() == b"\xef\xbb\xbfx\r\n"


def test_atomic_write_text_keeps_the_old_file_when_the_write_fails(tmp_path, monkeypatch):
    target = tmp_path / "keep.txt"
    target.write_text("old", encoding="utf-8")

    class Boom:
        def __str__(self):
            raise RuntimeError("encode failed halfway")
    with pytest.raises(Exception):
        fsutil.atomic_write_text(target, Boom())                                 # not a str: f.write raises
    assert target.read_text(encoding="utf-8") == "old" and [p.name for p in tmp_path.iterdir()] == ["keep.txt"]
    calls = _locked(monkeypatch, 99)                                             # the replace never works: tmp is cleaned up
    with pytest.raises(PermissionError):
        fsutil.atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "old" and [p.name for p in tmp_path.iterdir()] == ["keep.txt"] and calls["n"] == fsutil.REPLACE_TRIES
