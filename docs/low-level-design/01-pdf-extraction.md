# PDF Text Extraction — Low-Level Design

## 1. Purpose

Define the implementation contract, data model, validation behavior, error handling, and automated tests for extracting text from PDF documents.

This component is the first implementation milestone of the AI Document Intelligence Platform.

## 2. Scope

### Included

- Open and validate a PDF file.
- Extract text from each page independently.
- Preserve page numbers and document identity.
- Detect documents with no extractable text.
- Handle invalid and password-protected PDFs explicitly.
- Return structured extraction results.
- Provide automated tests for success and failure cases.

### Excluded

- Optical character recognition for scanned PDFs.
- Passage chunking and embedding generation.
- Vector indexing and semantic retrieval.
- LLM-based answer generation.
- API endpoints and user interface.

These capabilities will be addressed in later design documents.

## 3. Proposed Module

File: `src/ai_document_intelligence/ingestion/pdf_extractor.py`

The module is responsible only for PDF extraction and extraction-level validation. It must not perform chunking, embedding generation, or answer generation.

## 4. Proposed Data Model

### ExtractedPage

Each extracted page contains:

- `page_number`: one-based page number in the source PDF.
- `text`: extracted text for that page.

### ExtractedDocument

The document-level result contains:

- `document_id`: stable identifier assigned by the application.
- `source_name`: source filename or display name.
- `pages`: ordered collection of extracted pages.
- `page_count`: total number of pages in the PDF.

The document identifier must remain associated with every page when later components create passages.

## 5. Proposed Extraction Interface

The initial public function is:

`extract_pdf(path, document_id) -> ExtractedDocument`

The public interface and exception classes are defined in the implementation. See Sections 12 and 13.

The function must not silently convert extraction failures into successful empty results.

## 6. Processing Algorithm

1. Receive a PDF path and document identifier.
2. Attempt to open the document.
3. Validate that the document is a readable PDF.
4. Detect whether password authentication is required.
5. Read the total page count.
6. Iterate over pages in source order.
7. Extract text independently from each page.
8. Preserve the original one-based page number.
9. Build the structured document result.
10. If no page contains extractable text, report a distinct no-text condition.
11. Release document resources, including when an error occurs.

## 7. Error Handling

The implementation must distinguish these conditions:

| Condition | Expected behavior |
|---|---|
| File does not exist | Report a clear file-not-found error |
| Invalid or unreadable PDF | Report a clear invalid-document error |
| Password-protected PDF requiring a password | Report that authentication is required |
| Incorrect password, if password support is later added | Report an authentication failure |
| Valid PDF with no extractable text | Report a distinct no-text condition |
| Successful extraction | Return ordered page-level text and metadata |

The exception hierarchy is defined in Section 12. Exact error messages are implementation details; callers should rely on exception types.

## 8. Testing Design

Automated tests must cover:

1. A valid PDF containing text on one page.
2. A valid PDF containing text on multiple pages.
3. Preservation of one-based page numbers.
4. Preservation of document identity.
5. A missing file.
6. An invalid PDF file.
7. A valid PDF with no extractable text.
8. A password-protected PDF.
9. Resource cleanup after successful extraction and failure.

Test PDFs should be generated locally or created specifically for testing. Private user documents must not be committed to the repository.

## 9. Acceptance Criteria

The component is ready when:

- All required tests pass.
- Extracted text remains associated with the correct page.
- Page numbers are one-based and ordered.
- Document identity is preserved.
- Failure cases are distinguishable from successful extraction.
- Ruff checks pass.
- The public interface and its error behavior are documented.

## 10. Dependencies

PyMuPDF is used for PDF reading and text extraction. Its dependency is declared in `pyproject.toml`.

The project must verify the installed dependency and run the test suite before the feature is considered complete.

## 11. Concrete Python Data Structures

Use Python dataclasses for the initial data model.

### ExtractedPage

- `page_number: int`
- `text: str`

Page numbering is one-based and follows the source PDF order.

### ExtractedDocument

- `document_id: str`
- `source_name: str`
- `pages: list[ExtractedPage]`
- `page_count: int`

The caller supplies a non-empty document identifier. The extractor preserves that identifier; generating globally unique identifiers is outside this component's responsibility.

## 12. Exception Contract

Define `PDFExtractionError` as the base exception for extraction-specific failures.

Define these subclasses:

- `InvalidPDFError`: the file cannot be opened or processed as a valid PDF.
- `PDFPasswordRequiredError`: the PDF requires password authentication.
- `PDFNoExtractableTextError`: the PDF is valid, but no page yields extractable text.

A missing path raises Python's built-in `FileNotFoundError`.

The implementation must not expose low-level library exceptions as its public error contract unless they are deliberately preserved as exception causes.

## 13. Public Function Contract

`extract_pdf(path, document_id) -> ExtractedDocument`

The function validates the inputs, opens the PDF, extracts text page by page, preserves source metadata, and returns a structured result.

The PDF resource must be closed after successful extraction and after failures.

## 14. Initial Empty-Text Policy

For this version, if all pages contain no extractable text, raise `PDFNoExtractableTextError`.

OCR and recovery of text from image-only pages are outside the initial implementation scope.

## 15. Real-Document Validation

### Reference document

The initial real-document validation uses the following local reference:

- Document: US Patent 4,803,615, *Microcode Control of a Parallel Architecture Microprocessor*.
- Local reference path: supplied through the `REFERENCE_PDF_PATH` environment variable; the PDF is not stored in the repository.
- Page count reported by PyMuPDF: 14.
- Total extracted characters reported by the inspection script: 48,614.
- Pages inspected visually: 2, 3, 4, 10, and 11.
- Visual inspection outcome: the generated page previews were reported as legible.

These results are observations from a development inspection, not a substitute for
automated integration-test assertions.

### Visual-content limitations

The initial extraction component returns text and page metadata. It does not
interpret diagrams, determine relationships between figure elements, or guarantee
that all labels in a figure are searchable as text.

The inspection script reported image information on all 14 pages and zero vector
drawing objects. These counts alone do not establish that figures are semantically
understood or that all visual content is represented in extracted text.

Figure interpretation and image-based question answering remain outside the
initial extraction scope.

### Integration-test policy

- Keep deterministic, generated PDFs for unit tests covering success and failure
  cases.
- Use the real patent for local integration validation of text extraction and
  page provenance.
- Configure the reference PDF path through an environment variable rather than
  embedding a developer-specific absolute path in automated tests.
- Skip the real-document integration test with an explicit reason when the
  reference PDF is not configured or is unavailable.
- Do not commit the reference PDF to the repository.

The real-document integration test must verify the document's page count, the
presence of extracted text, and the preservation of one-based page numbers.
