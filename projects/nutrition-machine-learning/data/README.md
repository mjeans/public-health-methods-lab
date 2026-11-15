# Data provenance

The pipeline downloads only CDC/NCHS public-use NHANES files from `wwwn.cdc.gov`. The source manifest records URLs, sizes, cycles, and SHA-256 hashes. It rejects changed content after the manifest is established.

Raw XPTs stay in ignored `data/raw/`. Fitted models stay in ignored `artifacts/`; only load joblib files you created yourself, since untrusted serialized models can execute code. Respondent-level datasets and predictions are not published. All output tables and figures are aggregate research summaries.

The MIT license covers the project code and documentation, not a reassignment of rights to CDC data. Cite CDC/NCHS as the data source and follow its public-use documentation. Dates and cycles describe historical data, not a current clinical service.
