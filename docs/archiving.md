# Citable software archive

## Published archive: v1.1.0

[Public Health Methods Lab v1.1.0 on Zenodo](https://zenodo.org/records/24267623) is openly archived under the MIT License, with Matthew Jeans and ORCID [0000-0002-1140-3185](https://orcid.org/0000-0002-1140-3185) recorded as creator metadata.

- **Exact-version DOI:** [10.5281/zenodo.24267623](https://doi.org/10.5281/zenodo.24267623). Use this for reproducible citations.
- **All-versions DOI:** [10.5281/zenodo.24267622](https://doi.org/10.5281/zenodo.24267622). This identifies the software across archived versions and resolves to the latest one.
- **Release and source:** [v1.1.0](https://github.com/mjeans/public-health-methods-lab/releases/tag/v1.1.0), commit [`48003da919ed591c96e6603fbaf5ab9fd3033094`](https://github.com/mjeans/public-health-methods-lab/commit/48003da919ed591c96e6603fbaf5ab9fd3033094).
- **Publication date:** November 16, 2026 (Zenodo/UTC; November 15 in US Central time).
- **Archive verification:** the downloaded 168,343-byte ZIP matched Zenodo's MD5 checksum `972a86dd326c9d7a3d23a3bafd653dd8`; all 88 files matched the Git blob hashes of the released source tree, with no additional or missing files.

The main branch can evolve independently of this fixed archive. [CITATION.cff](../CITATION.cff) on main cites the latest verified archived release; the DOI was added after archiving, so the original ZIP does not contain that follow-up documentation. The source archive and existing tags were not replaced.

## Before publishing the next archive

1. Confirm that this repository remains enabled in the owner's Zenodo GitHub settings. [Connection instructions](https://help.zenodo.org/docs/github/enable-repository/) are available if reconnection is needed; the owner should review any requested access.
2. Confirm the intended main-branch commit has passed the core lab, nutrition ML, and research-artifact checks. Keep the commit SHA in the release notes.
3. Prepare release notes for the new version, using [v1.1.0's publication record](release-notes-v1.1.0.md) as a reference. Create a new GitHub release for the validated commit; do not overwrite existing tags or archives.
4. Allow Zenodo to ingest the new release, then verify the archive's title, creator, ORCID, license, files, version, and DOI on the actual record.
5. Only after verification, update the version-specific citation, version, and release date in CITATION.cff and the documentation. Keep the README badge on the all-versions DOI. Do not reuse an old version DOI for a new release.

The [Zenodo release-archiving guide](https://help.zenodo.org/docs/github/archive-software/github-upload/) explains the record and archival checks. [Zenodo metadata rules](https://help.zenodo.org/docs/github/describe-software/zenodo-json/) specify that .zenodo.json takes precedence over CITATION.cff for GitHub ingestion; keep title, creator, ORCID, and license consistent. The [.zenodo.json](../.zenodo.json) deliberately omits a fixed DOI so the integration can assign the appropriate DOI for each new archive.

## What the archive may contain

Source code, fixed designs, tests, aggregate tables, source-generated graphics, research briefs, public-source hashes, and documentation. No CDC respondent-level files, local caches, fitted model binaries, private research data, or original restricted TX Sprouts code.

A software DOI identifies an archived version. It does not confer peer review, clinical validity, or endorsement by CDC/NCHS or the authors of cited research.
