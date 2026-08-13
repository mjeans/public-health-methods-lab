# Nutrition epidemiology case study

## Question

How do energy-adjusted fiber and sodium densities differ between participants in a hypothetical nutrition-education program and a comparison group when two 24-hour recalls are available per person?

## Design

The analysis uses deterministic synthetic person-level dietary means. Each participant has two constructed recall days with day-to-day variation around a person-specific mean. The workflow:

1. averages energy and nutrient intake across the two recalls for each participant;
2. calculates fiber in grams and sodium in milligrams per 1,000 kilocalories;
3. summarizes completeness and group-specific means; and
4. estimates descriptive mean differences with normal-approximation 95% confidence intervals.

The energy-density approach makes nutrient comparisons less dependent on total reported energy intake. It does not eliminate correlated dietary measurement error or recover long-term usual intake.

## Reproducible outputs

- [Group summaries](../outputs/nutrition_density_summary.csv)
- [Group contrasts](../outputs/nutrition_group_contrasts.csv)
- [Generated findings](../outputs/summary.md)

## Interpretation boundaries

The data are synthetic and the groups are not randomized. Differences therefore demonstrate the calculation and reporting workflow, not the effect of nutrition education. Two recalls do not establish usual intake, underreporting and correlated errors are not modeled, no clinical or dietary-guideline classification is made, and the normal confidence intervals are illustrative for a small constructed sample.

A real nutritional-epidemiology analysis would prespecify the dietary assessment method, quality-control rules, energy-adjustment strategy, within-person variation model, covariates, survey design, missing-data approach, multiplicity plan, and population-specific interpretation.
