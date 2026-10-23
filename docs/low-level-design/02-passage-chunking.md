# Low-Level Design: PDF Passage Chunking

## 1. Purpose

Split extracted PDF page text into smaller passages suitable for later
retrieval and evidence-based question answering.

The component consumes the existing PDF extraction data model. It does not
open PDFs, perform OCR, generate embeddings, or answer questions.

## 2. Design Decisions

- Maximum passage length: 800 characters.
- Overlap between consecutive passages on the same page: 120 characters.
- Chunking is page-aware. A passage must not contain text from multiple pages.
- Prefer whitespace boundaries so passages do not split words unnecessarily.
- Preserve source document and page provenance in every passage.
- Empty or whitespace-only page text produces no passages.
- The real integration reference is US Patent 4,803,615.
- The reference PDF must remain outside the Git repository.

## 3. Input

The component accepts an `ExtractedDocument` produced by the existing
PDF extraction component.

The document contains:
- `document_id`
- `source_name`
- `pages`
- `page_count`

Each page contains:
- `page_number` (one-based)
- `text`

## 4. Output Data Model

Define an immutable `Passage` data class with these fields:

- `passage_id: str`
- `document_id: str`
- `source_name: str`
- `page_number: int`
- `text: str`

Every passage must preserve the source document ID, filename, and original
one-based page number.

## 5. Passage Identifier

Generate a deterministic passage ID from the document ID, page number, and
zero-based passage index on that page.

The same input document and chunking configuration must produce the same
passage IDs and ordering.

Passage IDs are identifiers, not cryptographic integrity guarantees.

## 6. Chunking Algorithm

Process pages in their original order. Chunk each page independently.

For each non-empty page:
1. Normalize neither the source text nor its internal whitespace globally.
2. Find a candidate end position no more than 800 characters after the
   current start position.
3. Prefer a whitespace boundary near the candidate end, without exceeding
   the maximum passage length.
4. If no suitable boundary exists, split at the maximum length.
5. Emit the passage with its source metadata.
6. Start the next passage up to 120 characters before the previous passage's
   end, ensuring forward progress.

The overlap is a target, not a reason to produce an empty or repeated passage.
The implementation must always advance and must terminate.

## 7. Invariants

- No passage exceeds 800 characters.
- Passage text is non-empty and contains non-whitespace content.
- Each passage belongs to exactly one source page.
- Page numbers remain one-based and unchanged.
- Passage order follows source page order and text order.
- Overlap does not cross page boundaries.
- Chunking a page must not silently omit its non-whitespace text.
- Repeated runs with the same input and configuration produce the same output.

## 8. Error Handling

- Reject invalid configuration, including a non-positive maximum size,
  negative overlap, or overlap greater than or equal to maximum size.
- Do not mutate the input extracted document.
- Use explicit exceptions for invalid chunking configuration.
- Empty pages are skipped rather than treated as extraction failures.

## 9. Testing Strategy

Unit tests must cover:
- A page shorter than the maximum size.
- A page exactly at the maximum size.
- A page longer than the maximum size.
- Overlap between adjacent passages.
- Word-boundary preference.
- A long token with no whitespace boundary.
- Empty and whitespace-only pages.
- Multiple pages with preserved one-based page numbers.
- Stable passage IDs and ordering.
- Invalid chunking configuration.
- No loss of non-whitespace source content.

Integration validation must use the real US Patent 4,803,615 through
the `REFERENCE_PDF_PATH` environment variable. It must verify that passages
are produced, lengths stay within the configured maximum, page provenance
is preserved, and passage IDs are unique and deterministic.

Generated PDFs may remain in unit tests for deterministic edge cases.
Do not commit the real patent PDF.

## 10. Out of Scope

- OCR and image-only PDF interpretation.
- Semantic or embedding-based chunking.
- Vector indexing and retrieval.
- LLM-based question answering.
- Cross-page passages.
