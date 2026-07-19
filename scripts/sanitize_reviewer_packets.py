#!/usr/bin/env python3
"""Rebuild the MF-PRISM reviewer packets from a strict public allowlist."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_IDS = ("01", "02", "03", "04", "05", "06", "08", "09")
FIXED_ZIP_TIME = (2026, 7, 18, 0, 0, 0)

PUBLIC_TOP_LEVEL = {
    "00_REVIEWER_README.md",
    "01_MANUSCRIPT.pdf",
    "02_MAIN_THEOREM.md",
    "03_SOURCE_PROBLEM_OR_CONJECTURE.md",
    "04_PROOF_DEPENDENCY_MAP.md",
    "05_LEMMA_CHECKLIST.md",
    "06_KNOWN_RISK_POINTS.md",
    "07_VERIFICATION_SCOPE.md",
    "08_REVIEW_REPORT_TEMPLATE.md",
    "09_RESPONSE_TO_REVIEWS.md",
}

ENTRY_RENAMES = {
    "00_REVIEWER_README.md": "00_REVIEWER_README.md",
    "01_CURRENT_MANUSCRIPT.pdf": "01_MANUSCRIPT.pdf",
    "01_MANUSCRIPT.pdf": "01_MANUSCRIPT.pdf",
    "01_MAIN_THEOREM.md": "02_MAIN_THEOREM.md",
    "02_MAIN_THEOREM.md": "02_MAIN_THEOREM.md",
    "02_SOURCE_PROBLEM_AND_CITATION.md": "03_SOURCE_PROBLEM_OR_CONJECTURE.md",
    "03_SOURCE_PROBLEM_OR_CONJECTURE.md": "03_SOURCE_PROBLEM_OR_CONJECTURE.md",
    "03_PROOF_DEPENDENCY_MAP.md": "04_PROOF_DEPENDENCY_MAP.md",
    "04_PROOF_DEPENDENCY_MAP.md": "04_PROOF_DEPENDENCY_MAP.md",
    "04_LEMMA_CHECKLIST.md": "05_LEMMA_CHECKLIST.md",
    "05_LEMMA_CHECKLIST.md": "05_LEMMA_CHECKLIST.md",
    "05_KNOWN_RISK_POINTS.md": "06_KNOWN_RISK_POINTS.md",
    "06_KNOWN_RISK_POINTS.md": "06_KNOWN_RISK_POINTS.md",
    "06_VERIFICATION_SCOPE.md": "07_VERIFICATION_SCOPE.md",
    "07_VERIFICATION_SCOPE.md": "07_VERIFICATION_SCOPE.md",
    "09_REVIEW_REPORT_TEMPLATE.md": "08_REVIEW_REPORT_TEMPLATE.md",
    "08_REVIEW_REPORT_TEMPLATE.md": "08_REVIEW_REPORT_TEMPLATE.md",
    "10_RESPONSE_TO_REVIEWS.md": "09_RESPONSE_TO_REVIEWS.md",
    "09_RESPONSE_TO_REVIEWS.md": "09_RESPONSE_TO_REVIEWS.md",
}

PAPER_METADATA = {
    "01": ("1.3", "10.5281/zenodo.21434379", "mf-prism-math-2026-01-v1.3-r1"),
    "02": ("1.3", "10.5281/zenodo.21434547", "mf-prism-math-2026-02-v1.3-r1"),
    "03": ("1.4", "10.5281/zenodo.21434562", "mf-prism-math-2026-03-v1.4-r1"),
    "04": ("1.2", "10.5281/zenodo.21434573", "mf-prism-math-2026-04-v1.2-r1"),
    "05": ("1.2", "10.5281/zenodo.21434602", "mf-prism-math-2026-05-v1.2-r1"),
    "06": ("2.2", "10.5281/zenodo.21434632", "mf-prism-math-2026-06-v2.2-r1"),
    "08": ("1.2", "10.5281/zenodo.21434694", "mf-prism-math-2026-08-v1.2-r1"),
    "09": ("1.1", "10.5281/zenodo.21434724", "mf-prism-math-2026-09-v1.1-r1"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_entry(name: str) -> str | None:
    if name in ENTRY_RENAMES:
        return ENTRY_RENAMES[name]
    if not name.startswith(("Verification/", "verification/")) or name.endswith("/"):
        return None
    leaf = name.rsplit("/", 1)[-1]
    if leaf.endswith((".py", ".txt")) and not leaf.startswith("internal_"):
        return f"verification/{leaf}"
    return None


def sanitize_reviewer_readme(data: bytes) -> bytes:
    text = data.decode("utf-8")
    lines = text.splitlines()
    cleaned: list[str] = []
    replacing_start_list = False
    public_start_list = [
        "1. `01_MANUSCRIPT.pdf`",
        "2. `02_MAIN_THEOREM.md`",
        "3. `03_SOURCE_PROBLEM_OR_CONJECTURE.md`",
        "4. `04_PROOF_DEPENDENCY_MAP.md`",
        "5. `05_LEMMA_CHECKLIST.md`",
        "6. `06_KNOWN_RISK_POINTS.md`",
        "7. `07_VERIFICATION_SCOPE.md`",
        "8. `verification/`",
        "9. `08_REVIEW_REPORT_TEMPLATE.md`",
        "10. `09_RESPONSE_TO_REVIEWS.md`",
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
        "`verification/verification_output.txt`",
    )
    text = text.replace("`Verification/", "`verification/")
    return (text.rstrip() + "\n").encode("utf-8")


def blank_response_log(data: bytes) -> bytes:
    text = data.decode("utf-8")
    paper_match = re.search(r"MF-PRISM-MATH-2026-\d{2}", text)
    if not paper_match:
        raise RuntimeError("Response log does not identify its paper")
    paper = paper_match.group(0)
    return (
        "# Response to Reviews\n\n"
        f"**Paper:** {paper}\n\n"
        "| Review comment | PRISM response | Manuscript change | Status |\n"
        "|---|---|---|---|\n"
        "|  |  |  | Open |\n"
    ).encode("utf-8")


def rebuild_packet(packet: Path) -> None:
    with zipfile.ZipFile(packet, "r") as source:
        entries: dict[str, bytes] = {}
        for info in source.infolist():
            canonical = canonical_entry(info.filename)
            if canonical is None:
                continue
            if canonical in entries:
                raise RuntimeError(f"{packet}: duplicate canonical entry: {canonical}")
            entries[canonical] = source.read(info.filename)
    entries["00_REVIEWER_README.md"] = sanitize_reviewer_readme(
        entries["00_REVIEWER_README.md"]
    )
    entries["02_MAIN_THEOREM.md"] = sanitize_main_theorem(
        entries["02_MAIN_THEOREM.md"]
    )
    entries["07_VERIFICATION_SCOPE.md"] = sanitize_verification_scope(
        entries["07_VERIFICATION_SCOPE.md"]
    )
    entries["09_RESPONSE_TO_REVIEWS.md"] = blank_response_log(
        entries["09_RESPONSE_TO_REVIEWS.md"]
    )

    missing = PUBLIC_TOP_LEVEL.difference(entries)
    if missing:
        raise RuntimeError(f"{packet}: missing required entries: {sorted(missing)}")
    if not any(name.startswith("verification/") for name in entries):
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


def update_zenodo_metadata(paper_id: str, paper_dir: Path) -> None:
    metadata_path = paper_dir / "zenodo.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    _version, _doi, tag = PAPER_METADATA[paper_id]
    replacement_url = f"https://github.com/MetriqOrg/PRISM/releases/tag/{tag}"
    supplemented = [
        related
        for related in metadata["related_identifiers"]
        if related.get("relation") == "isSupplementedBy"
    ]
    if len(supplemented) != 1:
        raise RuntimeError(f"{metadata_path}: expected exactly one isSupplementedBy entry")
    supplemented[0].update(
        identifier=replacement_url,
        scheme="url",
        resource_type="software",
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
        if current_paper and line.startswith("Planned GitHub tag: "):
            line = f"Planned GitHub tag: `{PAPER_METADATA[current_paper][2]}`"
        row_match = row.match(line)
        if current_paper and row_match:
            artifact = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{current_paper}" / row_match.group(2)
            if not artifact.is_file():
                raise RuntimeError(f"Manifest artifact not found: {artifact}")
            line = f"{row_match.group(1)}{row_match.group(2)}{row_match.group(3)}{sha256(artifact)}{row_match.group(5)}"
        updated.append(line)
    manifest.write_text("\n".join(updated) + "\n", encoding="utf-8", newline="\n")


def write_replacement_list() -> None:
    lines = [
        "# Zenodo Packaging-Revision Replacement List",
        "",
        "Replace only the three files listed for each record. Do not change any other artifact or metadata. Paper 05 remains an unpublished hold.",
        "",
        "| Identifier | Version DOI | Reviewer packet SHA-256 | SHA256SUMS.txt SHA-256 | zenodo.json SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for paper_id in PAPER_IDS:
        version, doi, _tag = PAPER_METADATA[paper_id]
        paper_dir = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{paper_id}"
        packet = next(paper_dir.glob("*_Reviewer_Packet_*.zip"))
        sums = paper_dir / "SHA256SUMS.txt"
        zenodo = paper_dir / "zenodo.json"
        lines.append(
            f"| `MF-PRISM-MATH-2026-{paper_id} v{version}` | `{doi}` | "
            f"`{sha256(packet)}` | `{sha256(sums)}` | `{sha256(zenodo)}` |"
        )
    lines.extend(["", "Paper 05 must not be published while its clarification hold remains active.", ""])
    (ROOT / "ZENODO_PACKAGING_REVISION_REPLACEMENTS.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )


def main() -> None:
    for paper_id in PAPER_IDS:
        paper_dir = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{paper_id}"
        packets = list(paper_dir.glob("*_Reviewer_Packet_*.zip"))
        if len(packets) != 1:
            raise RuntimeError(f"{paper_dir}: expected one reviewer packet, found {len(packets)}")
        rebuild_packet(packets[0])
        update_zenodo_metadata(paper_id, paper_dir)
        regenerate_paper_checksums(paper_dir)
    update_manifest()
    write_replacement_list()


if __name__ == "__main__":
    main()
