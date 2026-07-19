#!/usr/bin/env python3
"""Recursively audit repository and archive contents for public release safety."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


PROHIBITED = tuple(
    value.casefold()
    for value in (
        "LEARNING_" + "GUIDE_FOR_DANIEL",
        "Proof-Learning Guide for " + "Daniel H. Jeffery",
        "Learning " + "objectives",
        "Technical " + "self-test",
        "Daniel should " + "be able to answer",
        "INTERNAL_" + "AUDIT_REPORT",
        "proof " + "adoption",
        "proof-" + "adoption",
        "not yet " + "the sole",
        "not yet a mathematical " + "author",
        "final human " + "authorship",
        "authorship will " + "be determined",
        "before arXiv or " + "journal submission",
    )
)

FORBIDDEN_NAMES = {".ds_store", "__macosx"}
TEMP_SUFFIXES = ("~", ".bak", ".swp", ".tmp")
PDFTOTEXT = shutil.which("pdftotext") or str(
    Path.home()
    / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin/pdftotext"
)


def scan_text(label: str, text: str, failures: list[str]) -> None:
    folded = text.casefold()
    for phrase in PROHIBITED:
        if phrase in folded:
            failures.append(f"prohibited text in {label}: {phrase}")


def scan_pdf(label: str, data: bytes, failures: list[str]) -> None:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
        handle.write(data)
        handle.flush()
        result = subprocess.run(
            [PDFTOTEXT, handle.name, "-"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if result.returncode != 0:
        failures.append(f"PDF extraction failed for {label}")
        return
    scan_text(label, result.stdout.decode("utf-8", errors="replace"), failures)


def validate_entry_name(archive: str, name: str, failures: list[str]) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or str(path) != name.rstrip("/"):
        failures.append(f"unsafe archive path in {archive}: {name}")
    folded_parts = {part.casefold() for part in path.parts}
    if folded_parts.intersection(FORBIDDEN_NAMES):
        failures.append(f"forbidden metadata path in {archive}: {name}")
    if name.casefold().endswith(TEMP_SUFFIXES):
        failures.append(f"temporary/editor file in {archive}: {name}")
    scan_text(f"archive path {archive}!{name}", name, failures)


def scan_zip(label: str, data: bytes, failures: list[str], depth: int = 0) -> None:
    if depth > 8:
        failures.append(f"archive nesting too deep: {label}")
        return
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            bad_member = archive.testzip()
            if bad_member:
                failures.append(f"ZIP integrity failure in {label}: {bad_member}")
            names = [info.filename for info in archive.infolist()]
            if len(names) != len(set(names)):
                failures.append(f"duplicate ZIP entries in {label}")
            for info in archive.infolist():
                validate_entry_name(label, info.filename, failures)
                if info.is_dir():
                    continue
                member = archive.read(info.filename)
                member_label = f"{label}!{info.filename}"
                suffix = Path(info.filename).suffix.casefold()
                if suffix == ".zip":
                    scan_zip(member_label, member, failures, depth + 1)
                elif suffix == ".pdf":
                    scan_pdf(member_label, member, failures)
                else:
                    scan_text(member_label, member.decode("utf-8", errors="ignore"), failures)
    except zipfile.BadZipFile:
        failures.append(f"invalid ZIP file: {label}")


def iter_repository_files(root: Path):
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = [name for name in subdirs if name != ".git"]
        for filename in files:
            yield Path(directory) / filename


def main() -> int:
    roots = [Path(argument).resolve() for argument in sys.argv[1:]] or [Path.cwd()]
    failures: list[str] = []
    zip_count = 0
    pdf_count = 0
    for root in roots:
        for path in iter_repository_files(root):
            relative = str(path.relative_to(root))
            scan_text(f"path {relative}", relative, failures)
            suffix = path.suffix.casefold()
            if suffix == ".zip":
                zip_count += 1
                scan_zip(relative, path.read_bytes(), failures)
            elif suffix == ".pdf":
                pdf_count += 1
                scan_pdf(relative, path.read_bytes(), failures)
            else:
                scan_text(relative, path.read_text(encoding="utf-8", errors="ignore"), failures)
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Public-artifact audit passed: {zip_count} ZIPs and {pdf_count} standalone PDFs scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
