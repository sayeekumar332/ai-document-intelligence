# Source-Grounded Factual Answer Rubric

## Source of truth

- Source document: US Patent 4,803,615, "Microcode Control of a Parallel Architecture Microprocessor".
- Source file: `/Users/sayeekumars/Projects/US4803615.pdf`
- Extracted review text: `.tmp/US4803615_factual_review.txt`
- Purpose: Evaluate whether generated answers accurately represent the supplied patent.
- Status: Initial rubric; verify against the complete source before treating it as final.

## Evaluation principles

1. The supplied patent is the authority for this evaluation.
2. Accept paraphrases that preserve the source's meaning; exact wording is not required.
3. Allow an answer to combine supporting facts from multiple passages or pages.
4. Do not require one uniquely relevant passage when several passages support the answer.
5. Do not award factual credit for plausible external knowledge that the patent does not establish.
6. Distinguish explicit statements from reasonable inferences.
7. Preserve ambiguity, qualifications, and apparent inconsistencies in the source rather than silently resolving them.
8. If the patent does not establish a requested fact, the answer should say so.
9. A correct answer may be supported by multiple passages, but those passages must collectively support the claims made.
10. Judge answer-level factual fidelity separately from retrieval ranking and passage-level relevance.

## Questions and expected source-supported content

### Q1. What is the purpose of the microcode control store?

Expected content:
- Microinstructions are stored in the control store.
- An addressed access to the control store supplies the next microinstruction.
- The control store and control decodes generate major control signals based on microinstruction decodes.

Evidence: Pages 6–7; the abstract and description also establish the broader microinstruction sequencing context.

Do not require the answer to claim that the control store alone performs all decoding or sequencing logic.

### Q2. How does the processor select the next microinstruction address?

Expected content:
- The next-address field at the end of the current microinstruction is provided to the control decodes.
- The resulting information is passed to addressing logic in the instruction prefetch unit.
- The address produced by that logic is used to access the control store.

Evidence: Page 6.

Important qualification:
- The patent's described flow uses the next-address field to select the next microinstruction after the current microinstruction's micro-operations have completed successfully.
- Do not replace this description with an assumed conventional program-counter or branch mechanism.

### Q3. How does the invention handle successful and unsuccessful operations?

Expected content:
- A microinstruction contains multiple micro-operations that may require different subprocessors.
- Micro-operations whose required subprocessors are available can execute.
- Micro-operations that cannot execute because a required subprocessor is unavailable are retried in subsequent cycles.
- Successfully completed micro-operations are not repeated.

Evidence: Abstract; pages 5–7.

### Q4. What components make up the parallel architecture microprocessor?

Expected content:
The patent identifies five major units or subprocessor groups:
1. Instruction prefetch unit.
2. Register file and control.
3. Execution unit.
4. Channel interface unit.
5. Control store and control decodes.

The detailed description also discusses latch 19, which stores the microinstruction being executed.

Evidence: Pages 5–6.

Important qualification:
- Distinguish the five listed major groups from the latch discussed as part of microinstruction storage and sequencing.
- Accept a response that lists the five groups and separately mentions the latch.

### Q5. What happens when one or more micro-operations cannot execute successfully?

Expected content:
- Operations that cannot execute because their required subprocessors are unavailable are retried.
- Operations that can execute need not wait for every other operation to become executable.
- The current microinstruction remains in the latch until all of its micro-operations have completed.
- The next microinstruction is fetched when the current microinstruction's operations have completed.

Evidence: Abstract; pages 5–7.

Important qualification:
- Do not describe the invention as unconditionally repeating the entire microinstruction.
- The patent distinguishes retrying unsuccessful micro-operations from repeating operations that already succeeded.

### Q6. How does the processor avoid repeating micro-operations that have already completed?

Expected content:
- Successfully completed micro-operations are not executed again.
- The description explains that a no-operation signal is supplied for successful operations in the next cycle, while unsuccessful operations are repeated.

Evidence: Pages 6–7.

Important qualification:
- Credit explanations that accurately describe the no-operation behavior or otherwise correctly explain that completed operations are suppressed.
- Do not require the answer to reproduce implementation details beyond what the question asks.

### Q7. What role does the next-address field play in microinstruction sequencing?

Expected content:
- Once all micro-operations in the current microinstruction have completed, the next-address field is used to select the address of the next microinstruction.
- The selected address is used to access the control store, and the fetched microinstruction is placed in the latch.

Evidence: Page 6 and the flow description.

Important qualification:
- Do not imply that the processor advances to the next microinstruction while unsuccessful micro-operations from the current one remain unfinished.

### Q8. How do the subprocessors and control store interact during execution?

Expected content:
- The control store supplies microinstructions.
- Microinstruction information is held in latch 19 during execution.
- Control decodes generate major control signals and receive/process information about subprocessor availability.
- The next-address field is passed through the described control-decode and instruction-prefetch addressing path to select the next control-store access.
- Operations that cannot proceed because a required subprocessor is unavailable are retried, while completed operations are not repeated.

Evidence: Pages 6–7.

Important qualification:
- The answer may synthesize these details from different passages.
- Do not require every implementation detail if the answer accurately addresses the interaction asked about.

## Suggested answer-level scoring

Score each answer from 0 to 4.

- 4 — Accurate and sufficiently complete. All material claims are supported by the patent; paraphrasing and synthesis are acceptable.
- 3 — Substantially accurate. The core answer is correct, with a minor omission that does not change the meaning.
- 2 — Partially accurate. Some important source-supported content is present, but a material omission or ambiguity weakens the answer.
- 1 — Mostly unsupported or misleading. Only a small part is supported, or a significant claim conflicts with the source.
- 0 — Incorrect, contradicted by the source, or fails to answer the question.

For every answer, record:
- Score.
- Supporting source page(s) or passages.
- Material claims that are supported.
- Material claims that are unsupported or contradicted.
- Important omissions.
- Whether the answer appropriately acknowledges facts not established by the document.

## Evaluation safeguards

- Do not score an answer lower merely because it uses different terminology from the patent.
- Do not score an answer higher merely because it sounds technically plausible.
- Do not confuse retrieval relevance with answer correctness.
- If the patent supports several interpretations, record the ambiguity rather than forcing a single answer.
- Treat these criteria as preliminary until the complete extracted source has been reviewed.
