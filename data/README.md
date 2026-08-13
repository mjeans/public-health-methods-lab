# Data note

This lab does not include row-level health records. All dietary-recall means, surveillance counts, denominators, outbreak table cells, and retention times are deterministic synthetic fixtures defined in `scripts/run_analysis.py`.

The choice keeps every result reproducible while preventing the portfolio from normalizing unsafe handling of protected health information. A real workflow should separate public code from restricted data, document provenance and permissible use, enforce least-privilege access, and publish only disclosure-reviewed aggregates.
