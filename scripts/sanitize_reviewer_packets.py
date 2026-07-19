#!/usr/bin/env python3
"""Rebuild the MF-PRISM reviewer packets from a strict public allowlist."""

from __future__ import annotations

import hashlib
import re
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_IDS = ("01", "02", "03", "04", "05", "06", "08", "09")
FIXED_ZIP_TIME = (2026, 7, 18, 0, 0, 0)

PUBLIC_TOP_LEVEL = {
    "00_REVIEWER_README.md",
    "01_CURRENT_MANUSCRIPT.pdf",
    "01_MAIN_THEOREM.md",
    "02_SOURCE_PROBLEM_AND_CITATION.md",
    "03_PROOF_DEPENDENCY_MAP.md",
    "04_LEMMA_CHECKLIST.md",
    "05_KNOWN_RISK_POINTS.md",
    "06_VERIFICATION_SCOPE.md",
    "09_REVIEW_REPORT_TEMPLATE.md",
    "10_RESPONSE_TO_REVIEWS.md",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def public_entry(name: str) -> bool:
    if name in PUBLIC_TOP_LEVEL:
        return True
    if not name.startswith("Verification/") or name.endswith("/"):
        return False
    leaf = name.rsplit("/", 1)[-1]
    return leaf.endswith((".py", ".txt")) and not leaf.startswith("internal_")


def sanitize_reviewer_readme(data: bytes) -> bytes:
    text = data.decode("utf-8")
    lines = text.splitlines()
    cleaned: list[str] = []
    replacing_start_list = False
    public_start_list = [
        "1. `01_CURRENT_MANUSCRIPT.pdf`",
        "2. `01_MAIN_THEOREM.md`",
        "3. `02_SOURCE_PROBLEM_AND_CITATION.md`",
        "4. `03_PROOF_DEPENDENCY_MAP.md`",
        "5. `04_LEMMA_CHECKLIST.md`",
        "6. `05_KNOWN_RISK_POINTS.md`",
        "7. `06_VERIFICATION_SCOPE.md`",
        "8. `Verification/`",
        "9. `09_REVIEW_REPORT_TEMPLATE.md`",
        "10. `10_RESPONSE_TO_REVIEWS.md`",
    ]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Internal decision:**"):
            continue
        if stripped.startswith("This packet is designed for hostile mathematical review."):
            cleaned.append(
                "This packet is designed for independent mathematical review. Reviewers are asked to identify invalid inferences, missing hypotheses, counterexamples, incorrect imported-theorem use, source-problem ambiguity, and prior equivalent work."
            )
            continue
        if stripped == "## Start here":
            cleaned.append(line)
            cleaned.append("")
            cleaned.extend(public_start_list)
            replacing_start_list = True
            continue
        if replacing_start_list:
            if re.match(r"^\d+\. `", stripped) or not stripped:
                continue
            replacing_start_list = False
        cleaned.append(line.replace("Internal exact computation", "Included exact computation"))
    return ("\n".join(cleaned).rstrip() + "\n").encode("utf-8")


def sanitize_main_theorem(data: bytes) -> bytes:
    retained: list[str] = []
    for line in data.decode("utf-8").splitlines():
        if line.strip() == "## Internal decision":
            break
        retained.append(line)
    return ("\n".join(retained).rstrip() + "\n").encode("utf-8")


def sanitize_verification_scope(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace("What was checked internally", "What was checked")
    text = text.replace(
        "- No fatal logical defect was identified in the internal audit. The final classification still depends",
        "- The final classification depends",
    )
    text = text.replace(
        "- No fatal defect was identified. The main remaining issue is",
        "- The main remaining issue is",
    )
    text = text.replace(
        "- No fatal defect was identified. The main external questions are",
        "- The main external questions are",
    )
    text = text.replace(
        "`Verification/internal_rerun_output.txt`",
        "`Verification/verification_output.txt`",
    )
    return (text.rstrip() + "\n").encode("utf-8")


def rebuild_packet(packet: Path) -> None:
    with zipfile.ZipFile(packet, "r") as source:
        entries = {
            info.filename: source.read(info.filename)
            for info in source.infolist()
            if public_entry(info.filename)
        }
    entries["00_REVIEWER_README.md"] = sanitize_reviewer_readme(
        entries["00_REVIEWER_README.md"]
    )
    entries["01_MAIN_THEOREM.md"] = sanitize_main_theorem(
        entries["01_MAIN_THEOREM.md"]
    )
    entries["06_VERIFICATION_SCOPE.md"] = sanitize_verification_scope(
        entries["06_VERIFICATION_SCOPE.md"]
    )

    missing = PUBLIC_TOP_LEVEL.difference(entries)
    if missing:
        raise RuntimeError(f"{packet}: missing required entries: {sorted(missing)}")
    if not any(name.startswith("Verification/") for name in entries):
        raise RuntimeError(f"{packet}: no verification files retained")

    replacement = packet.with_suffix(".zip.tmp")
    with zipfile.ZipFile(
        replacement,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as target:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            target.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    replacement.replace(packet)


def regenerate_paper_checksums(paper_dir: Path) -> None:
    checksum_file = paper_dir / "SHA256SUMS.txt"
    artifact_files = sorted(
        path for path in paper_dir.iterdir() if path.is_file() and path != checksum_file
    )
    lines = [f"{sha256(path)}  {path.name}\n" for path in artifact_files]
    checksum_file.write_text("".join(lines), encoding="utf-8", newline="\n")


def update_manifest() -> None:
    manifest = ROOT / "FINAL_ZENODO_UPLOAD_MANIFEST.md"
    current_paper: str | None = None
    updated: list[str] = []
    heading = re.compile(r"^## MF-PRISM-MATH-2026-(\d{2}) ")
    row = re.compile(r"^(\| `)([^`]+)(` \| `)([0-9a-f]{64})(` \|)$")

    for line in manifest.read_text(encoding="utf-8").splitlines():
        heading_match = heading.match(line)
        if heading_match:
            current_paper = heading_match.group(1)
        row_match = row.match(line)
        if current_paper and row_match:
            artifact = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{current_paper}" / row_match.group(2)
            if not artifact.is_file():
                raise RuntimeError(f"Manifest artifact not found: {artifact}")
            line = f"{row_match.group(1)}{row_match.group(2)}{row_match.group(3)}{sha256(artifact)}{row_match.group(5)}"
        updated.append(line)
    manifest.write_text("\n".join(updated) + "\n", encoding="utf-8", newline="\n")


def write_replacement_list() -> None:
    doi_versions = {
        "01": ("1.3", "10.5281/zenodo.21434379"),
        "02": ("1.3", "10.5281/zenodo.21434547"),
        "03": ("1.4", "10.5281/zenodo.21434562"),
        "04": ("1.2", "10.5281/zenodo.21434573"),
        "05": ("1.2", "10.5281/zenodo.21434602"),
        "06": ("2.2", "10.5281/zenodo.21434632"),
        "08": ("1.2", "10.5281/zenodo.21434694"),
        "09": ("1.1", "10.5281/zenodo.21434724"),
    }
    lines = [
        "# Zenodo Reviewer-Packet Replacement List",
        "",
        "Replace only the two files listed for each record. Do not change any other artifact or metadata. Paper 05 remains an unpublished hold.",
        "",
        "| Identifier | Version DOI | Reviewer packet | SHA-256 | Checksum file | SHA-256 |",
        "|---|---|---|---|---|---|",
    ]
    for paper_id in PAPER_IDS:
        version, doi = doi_versions[paper_id]
        paper_dir = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{paper_id}"
        packet = next(paper_dir.glob("*_Reviewer_Packet_*.zip"))
        sums = paper_dir / "SHA256SUMS.txt"
        lines.append(
            f"| `MF-PRISM-MATH-2026-{paper_id} v{version}` | `{doi}` | "
            f"`{packet.name}` | `{sha256(packet)}` | `SHA256SUMS.txt` | `{sha256(sums)}` |"
        )
    lines.extend(["", "Paper 05 must not be published while its clarification hold remains active.", ""])
    (ROOT / "ZENODO_REVIEWER_PACKET_REPLACEMENTS.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )


def main() -> None:
    for paper_id in PAPER_IDS:
        paper_dir = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{paper_id}"
        packets = list(paper_dir.glob("*_Reviewer_Packet_*.zip"))
        if len(packets) != 1:
            raise RuntimeError(f"{paper_dir}: expected one reviewer packet, found {len(packets)}")
        rebuild_packet(packets[0])
        regenerate_paper_checksums(paper_dir)
    update_manifest()
    write_replacement_list()


if __name__ == "__main__":
    main()
