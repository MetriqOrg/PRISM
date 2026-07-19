# Release Quality-Control Report

## Scope

This report covers the final DOI-bearing candidate builds of Papers 01-06, 08, and 09.

## Completed checks for all eight papers

- The eight controlling DOI values were checked for uniqueness and matched paper by paper.
- Each final source ZIP was extracted into a clean directory; figure generation, exact/symbolic verification, and LuaLaTeX build targets completed successfully.
- Paper 09 passed both the supplied exact coefficient/operator verifier and the original SymPy verifier.
- PDF preflight confirmed all eight files are openable, unencrypted, text-based, letter-size PDFs with the expected pagination.
- `pdffonts` confirmed that every font is embedded.
- All 91 pages were rendered and visually inspected for wrapping, clipping, missing glyphs, and figure placement.
- The eight 300-dpi covers were regenerated from the final PDF page 1.
- Clean source ZIPs and reviewer packets were regenerated against the final PDFs and pagination.
- Every archive integrity test, internal archive manifest, and paper-level SHA-256 manifest passed.
- Placeholder scans covered repository text, PDF text, source ZIPs, and reviewer packets.

These checks are document and reproducibility controls, not independent mathematical review.

## Paper 09

Paper 09 Version 1.1 is complete. Its DOI-bearing nine-page PDF, 300-dpi cover, source/reproducibility ZIP, reviewer packet, metadata, predecessor record, and checksums are installed under `Papers/MF-PRISM-MATH-2026-09/`. Specialist priority review remains outstanding.

## Publication controls

No manuscript is represented as independently validated or peer reviewed. Paper 05 remains `HOLD FOR SOURCE-AUTHOR CLARIFICATION`; its reserved Zenodo draft must remain unpublished unless Daniel H. Jeffery explicitly clears that hold.
