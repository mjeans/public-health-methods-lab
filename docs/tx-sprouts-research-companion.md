# From nutrition research to inspectable methods

## Published work and documented contributions

[TX Sprouts food-processing analysis, Journal of Nutrition (2023)](https://doi.org/10.1016/j.tjnut.2023.04.013) examined a gardening, cooking, and nutrition intervention across 16 randomized elementary schools. The dietary analysis included 451 children and used repeated 24-hour recalls, NOVA food-processing categories, and mixed-effects models accounting for school clustering.

Matthew R. Jeans is the first author. The paper credits him with formal analysis and visualization; with Jaimie N. Davis, conceptualization, methodology, and preparation of the initial manuscript; and with the other authors, review and editing. The methods report Stata 17.

The findings differed by measurement: the paper reported increases in unprocessed/minimally processed food shares by calories and grams, and a decrease in ultra-processed food share by grams. It did not establish a statistically significant overall reduction in the ultra-processed calorie share.

[Read the paper, methods, author contributions, and data-availability statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC10375509/). Research data and original analytic code require an application; this portfolio does not redistribute them.

## Three review questions carried into this portfolio

These are present-day methodological reflections and new teaching examples, not a reconstruction of the original analysis.

**What is the independent unit?** In a school-assigned intervention, hundreds of pupils do not create hundreds of treatment assignments. The [clustering experiment](../projects/methods-stress-test/outputs/report.md#clustered-assignment) isolates that distinction using fictional, equal-size schools. Its school-mean t test is intentionally simpler than the published mixed-effects analysis.

**What is actually measured?** A short recall window and a long-term dietary exposure are different objects. The [measurement-error experiment](../projects/methods-stress-test/docs/methods.md#experiment-1-measurement-error) asks how noise and correlated reporting errors change a known slope. It does not validate NOVA classification or estimate a treatment effect.

**Who is represented by the observed outcomes?** An analysis can be computationally correct while answering a question about a selected subset. The [missing-outcome experiment](../projects/methods-stress-test/docs/methods.md#experiment-2-missing-outcomes) makes its selection mechanism explicit and demonstrates why an assumed correction can fail.

## Evidence to discuss in an interview

- Published research: a real collaborative study and explicitly documented contributions.
- [Methods simulation](../projects/methods-stress-test): newly written code, known generating truths, tests, and transparent failure cases.
- [Nutrition ML brief](../projects/nutrition-machine-learning/output/pdf/nutrition-ml-research-brief.pdf): a separate analysis of public-use NHANES data, not a result from the trial.

The examples connect research questions to auditable code while keeping original scholarship, illustrative simulations, and independent public-data analyses distinct. They do not imply that the original paper used these new scripts or that its restricted data have been reproduced here.
