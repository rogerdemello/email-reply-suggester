# Meta-evaluation: does the metric reflect real quality?

## 1. Discriminative validity (negative controls)

Mean overall score (1-5) by known-quality tier:

| Tier | Mean overall |
|------|-------------|
| gold | 3.487 |
| truncated | 2.113 |
| generic | 1.667 |
| offtopic | 1.946 |

Expected order: `gold > truncated > {generic, offtopic}`  ->  **ordering holds: True**

If the metric couldn't separate these tiers it wouldn't be measuring quality. The gold reply scores highest; an off-topic reply scores lowest, matching the human notes in the test set.

## 2. Convergent validity

Spearman rho (LLM judge vs embedding similarity), n=12: **0.885**

_positive-but-imperfect correlation is healthy: agree on direction, judge captures quality similarity misses_

## 3. Reliability (self-consistency)

Mean |overall_run1 - overall_run2| at temperature 0: **0.0**

_lower is better; ~0 means the metric is stable, not noise_
