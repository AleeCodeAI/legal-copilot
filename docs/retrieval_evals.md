# Retrieval Evaluation Methodology

## Purpose

This document defines the evaluation methodology for the retrieval stage of the Legal Copilot system.

The primary objective of evaluation is not to maximize arbitrary metrics, but to provide actionable feedback for improving the system. Every evaluation should clearly indicate which component requires improvement when performance degrades.

The retrieval pipeline consists of two independent components:

1. Complete Search
2. Retrieval Agent

These components have different responsibilities and are therefore evaluated independently.

This separation follows the overall architecture of the system, where each component has a single responsibility and communicates through well-defined interfaces.

---

# Evaluation Philosophy

The evaluation methodology follows several guiding principles.

## Evaluate Responsibilities, Not the Entire Pipeline

Each component should only be evaluated against the responsibility it owns.
The Complete Search is responsible for finding candidate evidence.
The Retrieval Agent is responsible for selecting sufficient evidence from those candidates.
Neither component should be evaluated for responsibilities that belong to another stage of the pipeline.

---

## Every Metric Must Support Engineering Decisions

Metrics are collected only if they help answer the question:

> What component should be improved next?

The evaluation intentionally avoids collecting a large number of metrics that provide little practical value.
Instead, it focuses on a small number of measurements that directly support debugging and system improvement.

---

## Sufficiency Over Completeness

The Legal Copilot is not designed to retrieve every relevant document.
Its objective is to retrieve enough evidence for the downstream Answer Synthesizer to produce a complete and accurate answer.
This distinction is fundamental.
A retrieval result is considered successful when it contains sufficient evidence, even if additional relevant chunks exist elsewhere in the corpus.

The system therefore optimizes for **minimal sufficient evidence**, not maximum evidence coverage.

---

# Evaluation Structure

The retrieval stage is evaluated through two independent evaluations.

| Evaluation                 | Component       | Primary Question                                                                                      |
| -------------------------- | --------------- | ----------------------------------------------------------------------------------------------------- |
| Complete Search Evaluation | Complete Search | Was the necessary evidence retrieved into the candidate set?                                          |
| Retrieval Agent Evaluation | Retrieval Agent | Given the candidate set, did the agent return sufficient evidence while avoiding unnecessary context? |

These evaluations intentionally measure different responsibilities.

---

# Evaluation 1 — Complete Search

## Purpose

The purpose of this evaluation is to measure retrieval recall.
The Complete Search does not need to identify the final evidence.
Its responsibility is simply to ensure that the evidence required to answer the question appears somewhere within the retrieved candidate set.
If the required evidence is present, the Complete Search has fulfilled its responsibility.
Filtering irrelevant information is not the responsibility of this stage.

---

## Ground Truth Dataset

A manually curated evaluation dataset is created.
Each evaluation sample contains:

* user query
* annotated chunk identifiers that contain the required evidence

These annotations represent the chunks that should be discoverable by retrieval.
Unlike the Retrieval Agent evaluation, exact chunk identifiers are appropriate here because the Complete Search is evaluated on retrieval recall rather than evidence sufficiency.

---

## Evaluation Procedure

For every evaluation query:

1. Execute the Complete Search.
2. Collect the retrieved candidate chunk identifiers.
3. Compare the retrieved identifiers against the annotated identifiers.
4. Compute retrieval performance.

The objective is to determine whether the required evidence entered the candidate set.
The evaluation does not assess ranking quality or filtering decisions.
Those responsibilities belong to the Retrieval Agent.

---

## Success Criterion

The Complete Search succeeds when the required evidence is retrieved.
It is acceptable for additional irrelevant candidates to appear in the results.
High recall is preferred over aggressive filtering because the Retrieval Agent performs evidence selection later in the pipeline.

---

# Evaluation 2 — Retrieval Agent

## Purpose

The Retrieval Agent is evaluated independently from the Complete Search.
Its responsibility is to identify a sufficient set of evidence from the candidate set returned by retrieval.
The agent is not evaluated on whether it retrieves every relevant chunk.
Instead, it is evaluated on whether the selected evidence is sufficient for the Answer Synthesizer to answer the user's question completely.

---

## Evaluation Philosophy

Traditional retrieval evaluation often compares retrieved documents against a predefined list of "correct" documents.
This approach is intentionally not used here.
Multiple combinations of chunks may provide sufficient evidence for answering a question.
Requiring the Retrieval Agent to reproduce one exact set of chunk identifiers would incorrectly penalize valid retrieval decisions.
Instead, the evaluation focuses on evidence sufficiency.

---

## Evaluation Dataset

Each evaluation sample contains:

* user query
* candidate chunks returned to the Retrieval Agent

These candidate chunks include:

* necessary evidence
* partially relevant evidence
* irrelevant distracting evidence

The Retrieval Agent receives exactly the same type of input that it would receive during normal system execution.

---

## Evaluation Procedure

For every evaluation sample:

1. Execute the Retrieval Agent.
2. Obtain the selected chunk identifiers.
3. Retrieve the corresponding chunk contents.
4. Submit the user query together with the selected chunk contents to an independent evaluation process.
5. Determine whether the selected evidence is sufficient to answer the query.

The evaluation focuses on the final evidence selected by the Retrieval Agent rather than the specific chunk identifiers it returns.

---

# Evidence Sufficiency Assessment

The Retrieval Agent is evaluated on one central question:

> Can the Answer Synthesizer produce a complete and accurate answer using only the selected evidence?

This question reflects the actual contract between the Retrieval Agent and the downstream Answer Synthesizer.
The evaluation therefore measures the usefulness of the selected evidence rather than agreement with predefined chunk identifiers.

---

# LLM Judge Calibration

## Purpose

An LLM Judge is used to automate evidence sufficiency assessment.
Before relying on the judge for large-scale evaluation, its decisions must first be calibrated against human judgments.
This process establishes confidence that the judge produces decisions similar to those of a human evaluator.
Calibration is performed infrequently.
Evaluation is performed continuously.

---

## Calibration Dataset

A representative collection of evaluation cases is selected.

Each case contains:

* user query
* retrieved evidence

The Retrieval Agent's internal reasoning, confidence, and decisions are **not** provided to the judge.
The judge evaluates only the evidence itself.
This prevents anchoring on the Retrieval Agent's conclusions.

---

## Human Evaluation

A human evaluator reviews each evaluation case and records:

* decision
* sufficient
* not sufficient
* short justification
* missing legal concepts (if insufficient)

The human judgment becomes the reference for calibration.

---

## LLM Judge Evaluation

The LLM Judge receives the same information.
It independently produces:

* decision
* short justification
* missing legal concepts (if insufficient)

The judge is not expected to reproduce identical wording.
Instead, agreement is measured primarily through decision consistency and identification of missing concepts.

---

## Calibration Objective

The objective is to determine whether the LLM Judge reaches decisions that consistently align with human evaluation.
Once acceptable agreement has been established, the LLM Judge may be used to evaluate larger datasets automatically.

---

# What Is Considered Success?

The Retrieval Agent succeeds when the selected evidence allows the downstream Answer Synthesizer to answer the user's question completely.
It is **not** required to retrieve every relevant chunk.
It is acceptable to omit relevant information that is unnecessary for answering the current question.
Likewise, including a small amount of additional evidence is not necessarily considered a failure if the selected evidence remains efficient and sufficient.
The primary objective is to return the smallest set of evidence that fully supports the requested answer.

---

# Design Principles

The evaluation methodology follows several architectural principles.

## Component Independence

Each evaluation measures only the responsibility assigned to that component.
Complete Search is evaluated independently from Retrieval Agent reasoning.

---

## Contract-Based Evaluation

Each component is evaluated against the contract it provides to the next stage of the pipeline.
Complete Search promises that necessary evidence is present in the candidate set.
The Retrieval Agent promises that the selected evidence is sufficient for answer generation.

---

## Evidence Sufficiency

Success is measured by evidence sufficiency rather than document completeness.
The system seeks enough evidence to answer the user's question, not every piece of related information.

---

## Practical Engineering

The evaluation methodology intentionally favors simplicity.
Rather than collecting numerous metrics, the evaluation focuses on measurements that directly inform engineering decisions and system improvements.
The objective is to create an evaluation process that remains understandable, maintainable, and useful throughout the continued development of the Legal Copilot.
