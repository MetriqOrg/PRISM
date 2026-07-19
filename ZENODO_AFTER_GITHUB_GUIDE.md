# Completing the Zenodo drafts after the GitHub migration

The eight version DOIs have already been reserved. Do not create replacement records.

## Wait for Codex and GitHub first

For each paper, wait until:

- the migration pull request is merged;
- the immutable GitHub tag/release exists;
- the final PDF, source ZIP, reviewer packet, and checksums have been generated from the merged source;
- the final upload manifest matches those files.

## Complete each draft

1. Open the existing unpublished draft in the `danielhjeffery` Zenodo account.
2. Confirm the reserved DOI matches `ZENODO_DOI_MAPPING.json`.
3. Creator: `Metriq PRISM Laboratory` as an organization, affiliation `Metriq Foundation, Inc.`
4. Contributor: `Jeffery, Daniel H.`, role `Project leader`, ORCID `0009-0001-1200-6042`.
5. Resource type: `Publication - Preprint`.
6. Add the final files listed in `FINAL_ZENODO_UPLOAD_MANIFEST.md`.
7. Add the immutable GitHub release as a related identifier using scheme `URL`; use `Is supplemented by` for source/reproducibility material.
8. Confirm license `CC BY 4.0` for the manuscript. The source archive contains the separate MIT notice for code.
9. Add the Metriq PRISM Laboratory community when available.
10. Preview the citation and file list.
11. Publish the draft only when the matching GitHub release is public.

## Paper 05

Keep DOI `10.5281/zenodo.21434602` as an unpublished draft until the source authors clarify the intended formulation or Daniel explicitly authorizes publication as a wording/interpretation note.

## ORCID

After each Zenodo record is published and the DOI resolves, add the work to ORCID using the DOI. Preserve the documented organizational-creator and corresponding-contributor credits.
