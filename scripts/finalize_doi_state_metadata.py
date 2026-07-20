#!/usr/bin/env python3
"""Finalize DOI-state metadata without changing research artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_METADATA = {
    "01": ("1.3", "10.5281/zenodo.21434379", "mf-prism-math-2026-01-v1.3-r2"),
    "02": ("1.3", "10.5281/zenodo.21434547", "mf-prism-math-2026-02-v1.3-r2"),
    "03": ("1.4", "10.5281/zenodo.21434562", "mf-prism-math-2026-03-v1.4-r2"),
    "04": ("1.2", "10.5281/zenodo.21434573", "mf-prism-math-2026-04-v1.2-r2"),
    "05": ("1.2", "10.5281/zenodo.21434602", "mf-prism-math-2026-05-v1.2-r2"),
    "06": ("2.2", "10.5281/zenodo.21434632", "mf-prism-math-2026-06-v2.2-r2"),
    "08": ("1.2", "10.5281/zenodo.21434694", "mf-prism-math-2026-08-v1.2-r2"),
    "09": ("1.1", "10.5281/zenodo.21434724", "mf-prism-math-2026-09-v1.1-r2"),
}
PUBLISHED_STATE = frozenset({"01", "02", "03", "04", "06", "08", "09"})
PUBLISHER = "Metriq Foundation, Inc."
CONTRIBUTOR = (
    "Organizational creator and issuer: Metriq PRISM Laboratory. "
    "Corresponding contributor: Daniel H. Jeffery, "
    "ORCID 0009-0001-1200-6042, prism@metriq.org."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def update_citation(paper_id: str, paper_dir: Path) -> None:
    citation = paper_dir / "CITATION.cff"
    text = citation.read_text(encoding="utf-8")
    if paper_id in PUBLISHED_STATE:
        old = 'description: "Reserved Zenodo DOI for this version"'
        new = 'description: "Zenodo DOI for this version"'
        if text.count(old) == 1:
            text = text.replace(old, new)
        elif text.count(new) != 1:
            raise RuntimeError(f"{citation}: expected one DOI description")
    citation.write_text(text, encoding="utf-8", newline="\n")


def add_publisher_after_publication_date(metadata: dict) -> dict:
    updated: dict = {}
    for key, value in metadata.items():
        updated[key] = value
        if key == "publication_date":
            updated["publisher"] = PUBLISHER
    if "publisher" not in updated:
        raise RuntimeError("publication_date not found while inserting publisher")
    return updated


def update_zenodo(paper_id: str, paper_dir: Path) -> None:
    _version, doi, tag = PAPER_METADATA[paper_id]
    metadata_path = paper_dir / "zenodo.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata = add_publisher_after_publication_date(metadata)

    supplemented = [
        related
        for related in metadata["related_identifiers"]
        if related.get("relation") == "isSupplementedBy"
    ]
    if len(supplemented) != 1:
        raise RuntimeError(f"{metadata_path}: expected one isSupplementedBy entry")
    supplemented[0].update(
        identifier=f"https://github.com/MetriqOrg/PRISM/releases/tag/{tag}",
        scheme="url",
        resource_type="software",
    )

    if paper_id in PUBLISHED_STATE:
        recorded_doi = metadata.pop("reserved_doi", metadata.get("doi"))
        if recorded_doi != doi:
            raise RuntimeError(f"{metadata_path}: reserved DOI mismatch")
        metadata["doi"] = doi
        metadata["notes"] = f"{CONTRIBUTOR} Version DOI: {doi}."
    else:
        if metadata.get("reserved_doi") != doi:
            raise RuntimeError(f"{metadata_path}: Paper 05 reserved DOI mismatch")
        metadata["notes"] = (
            f"{CONTRIBUTOR} Reserved version DOI: {doi}. "
            "The Zenodo record remains an unpublished draft and is on "
            "HOLD FOR SOURCE-AUTHOR CLARIFICATION until the source authors "
            "clarify the intended Problem 13 formulation or publication is "
            "explicitly authorized."
        )

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def regenerate_checksums(paper_dir: Path) -> None:
    checksum_file = paper_dir / "SHA256SUMS.txt"
    artifacts = sorted(
        path for path in paper_dir.iterdir() if path.is_file() and path != checksum_file
    )
    checksum_file.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts),
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
        if current_paper and line.startswith("Reserved DOI: ") and current_paper in PUBLISHED_STATE:
            line = line.replace("Reserved DOI:", "Version DOI:", 1)
        row_match = row.match(line)
        if current_paper and row_match:
            artifact = (
                ROOT
                / "Papers"
                / f"MF-PRISM-MATH-2026-{current_paper}"
                / row_match.group(2)
            )
            if not artifact.is_file():
                raise RuntimeError(f"Manifest artifact not found: {artifact}")
            line = (
                f"{row_match.group(1)}{row_match.group(2)}{row_match.group(3)}"
                f"{sha256(artifact)}{row_match.group(5)}"
            )
        updated.append(line)
    manifest.write_text("\n".join(updated) + "\n", encoding="utf-8", newline="\n")


def write_replacement_list() -> None:
    lines = [
        "# Zenodo DOI-State Metadata Replacement List",
        "",
        "Replace only `CITATION.cff`, `SHA256SUMS.txt`, and `zenodo.json` for each record. Do not change any other artifact. Paper 05 remains an unpublished hold.",
        "",
        "| Identifier | Version DOI | CITATION.cff SHA-256 | SHA256SUMS.txt SHA-256 | zenodo.json SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for paper_id, (version, doi, _tag) in PAPER_METADATA.items():
        paper_dir = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{paper_id}"
        lines.append(
            f"| `MF-PRISM-MATH-2026-{paper_id} v{version}` | `{doi}` | "
            f"`{sha256(paper_dir / 'CITATION.cff')}` | "
            f"`{sha256(paper_dir / 'SHA256SUMS.txt')}` | "
            f"`{sha256(paper_dir / 'zenodo.json')}` |"
        )
    lines.extend(
        [
            "",
            "Paper 05 must not be published while its source-author-clarification hold remains active.",
            "",
        ]
    )
    (ROOT / "ZENODO_PACKAGING_REVISION_REPLACEMENTS.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )


def main() -> None:
    for paper_id in PAPER_METADATA:
        paper_dir = ROOT / "Papers" / f"MF-PRISM-MATH-2026-{paper_id}"
        update_citation(paper_id, paper_dir)
        update_zenodo(paper_id, paper_dir)
        regenerate_checksums(paper_dir)
    update_manifest()
    write_replacement_list()


if __name__ == "__main__":
    main()
