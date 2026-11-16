# Citable software archive

The repository includes [CITATION.cff](../CITATION.cff), [Zenodo metadata](../.zenodo.json), MIT licensing, aggregate-only publication boundaries, and automated validation. These prepare the software for an archive; **they do not by themselves create a DOI**.

## Before publishing the next archive

1. Sign in to your own Zenodo account and [connect GitHub, then enable this repository](https://help.zenodo.org/docs/github/enable-repository/). Review the requested access in the service's own authorization screen.
2. Confirm the intended main-branch commit has passed the core lab, nutrition ML, and research-artifact checks. Keep the commit SHA in the release notes.
3. Review [the prepared release notes](release-notes-v1.1.0.md). Create a new GitHub release for the validated commit; do not overwrite the existing v1.0.0 tag.
4. Allow Zenodo to ingest the new release, then verify the archive's title, creator, ORCID, license, files, version, and DOI on the actual record.
5. Only after verification, add the real DOI badge and citation link to this repository and the profile. Do not invent a DOI or present archive preparation as publication.

The [Zenodo release-archiving guide](https://help.zenodo.org/docs/github/archive-software/github-upload/) explains the record and archival checks. [Zenodo metadata rules](https://help.zenodo.org/docs/github/describe-software/zenodo-json/) specify that .zenodo.json takes precedence over CITATION.cff for GitHub ingestion; keep both consistent.

## What the archive may contain

Source code, fixed designs, tests, aggregate tables, source-generated graphics, research briefs, public-source hashes, and documentation. No CDC respondent-level files, local caches, fitted model binaries, private research data, or original restricted TX Sprouts code.

A software DOI identifies an archived version. It does not confer peer review, clinical validity, or endorsement by CDC/NCHS or the authors of cited research.
