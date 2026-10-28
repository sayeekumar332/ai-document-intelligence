# Retrieval Evaluation — V1 Record

## Status

**V1 evaluation record; relevance judgments are provisional and not validated.**

This directory preserves the retrieval-evaluation artifacts associated with the V1 implementation checkpoint. The purpose is to make the evaluation evidence reviewable and establish a consistent reference for future comparisons. The recorded scores must not be interpreted as validated claims about production retrieval quality.

## Implementation checkpoint

- Repository checkpoint: `26f4160`
- Checkpoint description: merge of the semantic retrieval design into `main`
- Retrieval entry point evaluated: `RetrievalService.retrieve()`
- Benchmark questions: 8
- Metrics: Precision@5, judged-relevant Recall@5, and nDCG@5
- Database writes by the evaluation script: none, according to the saved report

The checkpoint identifies the implementation reference. This directory preserves evaluation artifacts; it does not change the retrieval implementation or database.

## Evaluation results

The values below are the macro averages recorded in `retrieval_metrics.txt`.

| Version | Precision@5 | Judged-relevant Recall@5 | nDCG@5 |
|---|---:|---:|---:|
| NEW | 0.775 | 0.764 | 0.770 |
| BASELINE | 0.800 | 0.702 | 0.618 |

### Interpretation

- NEW has higher judged-relevant Recall@5 and nDCG@5 in this evaluation run.
- BASELINE has slightly higher Precision@5.
- The results describe the eight-question benchmark and its current judgments; they do not establish general performance across other documents or queries.
- The relevance judgments are explicitly provisional. Metric comparisons are diagnostic until the judgments have been reviewed and validated.

### Metric and judgment caveats

- The saved report uses judged-relevant Recall@5, with the denominator based on relevant passages judged for each question and version.
- Unjudged retrieved passages receive zero gain in the recorded evaluation; judgment coverage is also reported.
- The benchmark is small and may not represent the diversity of real user queries.
- Human review and validation of relevance judgments remain necessary before treating the metrics as a stable quality claim.

## Source-grounded factual-answer rubric

`factual_answer_rubric.md` records criteria for evaluating answers against the source document. The document is the source of truth for source-fidelity review:

- Accept paraphrases when they preserve the source meaning.
- Allow multiple passages to jointly support an answer.
- Do not accept plausible external knowledge as evidence when the source does not support it.
- Preserve ambiguity and inconsistencies rather than silently resolving them.
- When the document does not establish a fact, the answer should say so.

This rubric is a review artifact for source-grounded answer evaluation. Its presence does not imply that an answer-generation module is implemented or that the answers have been automatically evaluated.

## Rejected context-reranking experiment

`context_reranking_report.txt` preserves the experiment and its comparison with the baseline retrieval path. The experiment was rejected for V1 because the reported metrics degraded for both NEW and BASELINE, and the context results included fewer judged passages.

The experiment remains available as historical evidence. It is **not part of the V1 implementation**, and its results should not be combined with the primary metrics above.

## Files in this record

- `retrieval_eval_questions.json` — the eight-question benchmark.
- `retrieval_relevance_judgments.json` — schema-versioned relevance judgments, currently marked provisional.
- `retrieval_metrics.txt` — selected metrics report from the completed Q4 judgment pass.
- `factual_answer_rubric.md` — source-grounded answer-review criteria.
- `evidence_packet.json` — retrieved passages preserved for manual evidence review; it does not automatically determine factual sufficiency.
- `context_reranking_report.txt` — record of the rejected context-reranking experiment.

The source artifacts in `.tmp/` were copied into this directory; the originals were not intended to be modified by this preservation step.

## Reproduction and future comparisons

The saved reports are the record of this evaluation run. Reproducing the retrieval metrics may require the repository's compatible Python environment, dependencies, local embedding-model availability, configured database, indexed passages, and the relevant evaluation scripts. Do not assume the saved artifacts alone reproduce a fresh run.

For V2 and later comparisons:

1. Keep the V1 artifacts unchanged as the reference record.
2. Use the same benchmark questions and evaluation definitions when making a direct comparison.
3. Record changes to judgments, data, models, configuration, or retrieval logic explicitly.
4. Report regressions as well as improvements.
5. Validate relevance judgments before making stronger quality claims.
6. Keep experimental approaches separate from the accepted implementation until their evidence supports adoption.

## Scope

This record documents retrieval evaluation and associated review artifacts. It does not claim that all possible queries have been tested, that the provisional judgments are validated, or that the rejected context-reranking experiment is integrated.
