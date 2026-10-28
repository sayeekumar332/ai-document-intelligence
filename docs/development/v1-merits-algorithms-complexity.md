# V1 Approach: Merits, Limitations, Algorithms, and Complexity

## 1. Purpose and status

This document describes the V1 implementation of the AI Document Intelligence
Platform, including its strengths, limitations, algorithms, and asymptotic
time and space complexity.

It is based on the implementation in:

- `src/ai_document_intelligence/ingestion/pdf_extractor.py`
- `src/ai_document_intelligence/ingestion/passage_chunker.py`
- `src/ai_document_intelligence/embeddings/embedding_generator.py`
- `src/ai_document_intelligence/retrieval/postgres_vector_index.py`
- `src/ai_document_intelligence/retrieval/retrieval_service.py`

V1 implements **PDF text ingestion, passage chunking, local text embeddings,
PostgreSQL/pgvector persistence, and semantic passage retrieval**. It does
not yet implement a complete question-answering product: there is no
source-grounded LLM answer generator, answer-sufficiency classifier, public
API, or user interface in this version.

The complexity estimates below describe algorithmic growth under stated
assumptions. They are not benchmark results, latency guarantees, or claims
about a particular computer's throughput.

## 2. V1 at a glance

| Area | Implemented approach |
|---|---|
| PDF processing | PyMuPDF text extraction, page by page |
| Chunking | Deterministic, page-aware character chunks; default maximum 800 characters and 120-character overlap |
| Passage identity | Document ID + one-based page number + passage index on that page |
| Embeddings | Local Sentence Transformers model `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding vector | 384 floating-point dimensions; normalized embeddings |
| Persistence | PostgreSQL with pgvector, plus ordinary relational metadata |
| Similarity | Exact cosine-distance search via pgvector's `<=>` operator |
| Ranking | Ascending cosine distance; passage ID breaks ties |
| Retrieval orchestration | Embed query, retrieve an expanded candidate set, suppress normalized duplicate text |
| Evaluation record | Precision@5, judged-relevant Recall@5, and nDCG@5 on an eight-question benchmark |

The model maps text into 384-dimensional vectors. Its published model card
states that the default configuration truncates inputs longer than 256
word pieces. See the [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and the [Sentence Transformers documentation on sequence length](https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html).

## 3. AI and retrieval algorithms used

### 3.1 Pretrained Transformer sentence embeddings

**What it does:** The embedding generator sends passage text (and, at query
time, the user query) through the pretrained
`sentence-transformers/all-MiniLM-L6-v2` sentence encoder. The result is a
dense 384-dimensional vector. The implementation requests normalized
embeddings and validates their dimensions and finite numeric values.

**What V1 does not do:** It does not train or fine-tune the model. The
contrastive training described by the model's published card belongs to the
pretrained model's development, not to this project's runtime pipeline.
The application runs inference using that model.

**Role in retrieval:** Semantically related text can have nearby vectors even
when it does not share the exact same words. Embedding quality therefore
influences the passages that can be found.

### 3.2 Exact cosine-similarity retrieval

The PostgreSQL index computes cosine distance using pgvector's `<=>`
operator and sorts the results in ascending distance order. The score
returned by the adapter is calculated as:

```text
similarity score = 1 - cosine distance
```

A passage ID is used as a stable tie-breaker when distances are equal. The
query can optionally filter rows by `document_id` before ranking and limiting
the results.

This is **exact nearest-neighbour search**, not approximate nearest-neighbour
search. V1 has a B-tree index on `document_id`, but it does not have a
pgvector HNSW or IVFFlat index to accelerate vector ranking across a large
unfiltered corpus.

### 3.3 Deterministic overlapping chunking

The chunker processes pages independently, normally using a maximum of 800
characters and 120 characters of overlap. When possible, it prefers a
paragraph boundary, then a sentence-ending boundary, then whitespace; it
falls back to the permitted character limit when needed.

This is a deterministic text-processing algorithm, not a learned AI model.
Page boundaries are preserved so that each passage retains its source page.

### 3.4 Normalized text duplicate suppression

After retrieval, the service converts candidate passage text to lowercase
using Python's `casefold()` and collapses whitespace. It keeps the first
candidate for each normalized text, preserving the highest-ranked occurrence
and its original provenance.

This is **literal normalized-text deduplication**, not semantic deduplication.
It does not identify different phrasings that express the same idea.

### 3.5 Retrieval evaluation metrics

The saved V1 evaluation record reports Precision@5, judged-relevant
Recall@5, and nDCG@5. These are evaluation metrics; they are not part of the
online retrieval algorithm itself.

The benchmark has eight questions and the relevance judgments are marked
**provisional and not validated**. The results are diagnostic and should not
be presented as validated production-quality claims. See
[the V1 evaluation record](retrieval-evaluation-v1/README.md).

### 3.6 Techniques not implemented in V1

- **LLM answer generation:** not implemented; the retriever returns passages.
- **OCR:** not implemented for image-only/scanned PDF pages.
- **Hybrid lexical + vector search:** no BM25 or keyword retrieval is combined with vector search.
- **Neural reranking in the accepted path:** not used. The documented context-reranking experiment was rejected for V1 after its reported metrics degraded for both NEW and BASELINE.
- **Approximate vector index:** no HNSW or IVFFlat index is created.
- **Automatic evidence-sufficiency or contradiction detection:** not implemented.

## 4. Merits of the current approach

### 4.1 Local execution and data control

PDF extraction and embedding inference run locally once the dependencies and
model files are available. This avoids a required paid hosted embedding API
and keeps the passage text off an external inference service in the current
embedding component. PostgreSQL is also hosted locally in the documented
Docker Compose environment.

### 4.2 Traceable evidence

Each passage retains a document ID, source filename, and one-based page number.
The deterministic passage ID includes the document ID, page number, and
passage index. This makes retrieved passages easier to trace to their source
and supports future citation features.

### 4.3 Relatively simple and auditable retrieval

Cosine-distance ranking is a straightforward baseline to explain and test.
The SQL ranking includes a deterministic tie-breaker. Exact search avoids the
recall approximation introduced by approximate-nearest-neighbour algorithms,
though it has higher growth cost as the corpus expands.

### 4.4 Persistent, transactional storage

PostgreSQL stores the passage text, provenance, and embedding together.
The adapter validates an upsert batch before writing and uses one transaction
for the batch. Schema metadata checks model name, dimension, encoding, metric,
and schema version, reducing the risk of silently reusing a visibly
incompatible index.

### 4.5 Modular design and testability

Extraction, chunking, embedding generation, vector persistence, and query
orchestration are separated into Python components. Dependencies can be
injected into the embedding and retrieval components, allowing deterministic
unit tests without model downloads or database connections for every test.

### 4.6 A documented baseline for iteration

The V1 evaluation artifacts preserve questions, judgments, metrics, evidence,
and caveats. That record gives future experiments a reference point, provided
the benchmark and judgment changes are explicitly tracked and the judgments
are validated before stronger quality claims are made.

## 5. Limitations and risks

### 5.1 Retrieval quality is not yet validated

The V1 evaluation contains only eight questions, and relevance judgments are
provisional. It cannot establish general performance across documents,
industries, writing styles, or user queries. Broader testing and validated
human judgments are needed.

### 5.2 Text-only PDF ingestion

PyMuPDF extracts text from PDF pages, but V1 does not OCR scanned pages or
understand figures, diagrams, tables as visual structures, or page layout
semantics. A PDF can open successfully and still lack searchable text.

### 5.3 Character-based rather than semantic/token-aware chunks

The chunker uses character counts and simple boundary heuristics. It does not
guarantee that a passage corresponds to a complete idea or section. Overlap
helps preserve context at boundaries, but increases stored text and may
produce near-duplicate passages.

The embedding model's default 256-word-piece limit is another constraint.
If a passage tokenizes beyond that limit, the model truncates the input; the
tail of that passage may not influence its embedding. Character count does
not precisely predict token count.

### 5.4 Embeddings can miss exact identifiers and domain-specific detail

Dense sentence embeddings are useful for semantic similarity, but may not
always rank exact part numbers, rare names, legal identifiers, long numeric
strings, or domain-specific expressions as desired. V1 does not complement
vector search with lexical/BM25 matching or a reranker in the accepted path.

### 5.5 Exact search grows linearly with corpus size in distance work

Without an approximate vector index, an unfiltered query calculates a vector
distance for each of the `M` stored passages. For fixed vector dimension,
distance calculation grows linearly with `M`; ranking adds sorting work.
This is simple and exact but may become a latency bottleneck as the corpus
grows.

The B-tree index on `document_id` helps document-level filtering, not general
vector-neighbour search. PostgreSQL's chosen plan and available memory affect
the actual work performed.

### 5.6 Duplicate suppression is limited

The service removes case- and whitespace-normalized textual duplicates only
from the retrieved candidate list. It does not merge semantically similar
passages, and it may return fewer than `top_k` results if it cannot find
enough unique non-empty passages among the candidates.

The candidate count is normally up to four times `top_k`, capped at 200;
if `top_k` itself exceeds 200, the implementation uses at least `top_k`
candidates.

### 5.7 No end-to-end answer safeguards yet

The retriever does not determine whether evidence is sufficient, resolve
conflicting passages, generate answers, or produce final source citations.
Those responsibilities must be implemented and evaluated separately before
the system is described as a completed document question-answering product.

### 5.8 Model identity and deployment are constrained

The index stores the model name and embedding dimension, but the incoming
`EmbeddedPassage` record does not include a model revision for each vector.
The caller remains responsible for ensuring that stored passage embeddings
and query embeddings come from a compatible model/configuration.

Local inference still requires memory for the model and its activations.
A first download may be needed if the model is not cached, unless offline
mode is required (in which case missing model files cause loading to fail).

### 5.9 Runtime and resource benchmarks are still required

Big-O analysis alone cannot tell whether a query will complete in a specific
number of milliseconds or how many documents fit on a particular machine.
Latency, throughput, memory, disk footprint, and performance under concurrent
queries have not been established by the design or evaluation record quoted
here. Measure them with representative documents and queries before claiming
production capacity.

## 6. Complexity notation and assumptions

The estimates below use these symbols:

| Symbol | Meaning |
|---|---|
| `P` | Number of PDF pages |
| `S` | Total characters extracted from the document(s) |
| `C` | Number of passages produced for ingestion |
| `M` | Number of passages already stored in the index before a query |
| `d` | Embedding dimension; 384 in the default configuration |
| `L` | Token sequence length processed per passage; at most 256 word pieces under the model's default truncation behavior |
| `H` | Transformer hidden size; 384 for this model family |
| `A` | Transformer layer count; 6 for MiniLM-L6 |
| `B` | Embedding batch size; default 32 |
| `k` | Requested `top_k` |
| `q` | Number of candidates requested from the index: `max(k, min(4k, 200))` |

The model facts (`d=384`, `H=384`, `A=6`, and the default
256-word-piece truncation behavior) are from the model documentation linked
in Section 2. `L` depends on the actual tokenized text, up to that limit.
These symbols simplify the analysis; model/kernel operations, I/O, and
database query plans affect wall-clock time.

## 7. Time and space complexity by stage

### 7.1 PDF text extraction

Let `S` be the total extracted text size.

- **Time:** approximately `O(P + S)` for the high-level page traversal and output construction. Actual PDF parsing cost also depends on file size and internal PDF structure; this is not a formal worst-case bound for PyMuPDF.
- **Working space:** `O(P + S)` for the returned in-memory page records, excluding parser-internal structures and the PDF file's binary representation.

### 7.2 Passage chunking

With the V1 defaults `max_chars = 800` and `overlap_chars = 120`, the
boundary scan for each chunk is bounded by a fixed-size window.

- **Time:** (O`S`) for fixed chunk and overlap settings.
- **Output space:** `O(S + C)`. Overlap copies some source characters into adjacent passages, so total passage text can exceed `S`; `C` additional passage records and IDs are created.
- **Configuration caveat:** the chunk settings are configurable. Very large overlap relative to chunk size can greatly increase the number of iterations and repeated boundary scanning. The linear statement is for the fixed V1 settings, not every possible parameter combination.

### 7.3 Embedding generation

For a dense Transformer encoder, a standard per-passage operation estimate is:

```text
O\left(A\left(L^2H + LH^2\right)\right)
```

The `L^2 H` term represents self-attention work, and the `L H^2` term
captures dense projection/feed-forward work up to architecture-specific
constant factors. For `C` passages:

```text
O\left(CA\left(L^2H + LH^2\right)\right)
```

- **Time:** above operation estimate plus tokenization and vector validation. With the fixed model and bounded input length, `L`, `H`, and `A` are bounded constants, so the embedding computation is (O`C`) with respect to the number of passages.
- **Output space:** `O(Cd)` for all generated vectors, in addition to passage text and provenance. The implementation returns all generated embeddings in a list.
- **Inference working memory:** approximately `O(B(L^2 + LH))` for sequence-dependent activations, with architecture/implementation constants omitted, plus resident model weights and `O(Cd)` for retained outputs. Actual memory depends on PyTorch, device, and batching internals.

This is an operation-count model, not a prediction of seconds. Neural inference is normally the most computationally expensive ingestion stage, but the relative cost should be confirmed by profiling.

### 7.4 Validate and upsert embedded passages

For `C` new or updated passages with `d`-dimensional vectors:

- **Application validation time:** `O(Cd + S_p)`, where `S_p` is the total passage-text size being validated/copied.
- **Database writes:** one transactional batch containing `C` parameterized upserts. With primary-key and document B-tree maintenance, a useful rough growth model is `O(C log M + Cd + S_p)`, excluding database page I/O, locks, WAL, and other PostgreSQL implementation costs.
- **Application working space:** `O(Cd + S_p)`, because the adapter materializes the input sequence and validated records before the transactional write.
- **Persistent space:** passage text, metadata, vectors, table overhead, and indexes grow with the number of stored rows.

The database costs are indicative, not strict bounds on PostgreSQL's internal execution.

### 7.5 Query embedding

Let `L_q` be the token count for a single query (bounded by the model's
default truncation limit).

- **Time:** `O(A(L_q^2 H + L_q H^2))`, plus tokenization and vector validation.
- **Output space:** (O`d`) for the query vector.
- **Working space:** model weights plus query-sequence activations; with a fixed model and one query, this is bounded independently of `M`, the corpus size.

### 7.6 Exact cosine retrieval and ranking

The vector index evaluates cosine distance using the SQL expression
`embedding <=> query_vector` and orders rows by distance, then passage ID.

For `M` considered rows:

- **Distance calculations:** `O(Md)`.
- **Ranking:** conservative worst-case bound `O(M log M)`. When PostgreSQL uses a bounded top-`q` sort for a `LIMIT q` query, ranking can be closer to `O(M log q)`. The actual sort method depends on the query plan.
- **Overall query time for index search:** `O(Md + M log M)` as a conservative bound. Because `d=384` is fixed, this grows approximately linearly with `M` for fixed result limits, but the ranking and I/O terms matter in practice.
- **Space:** database execution workspace depends on PostgreSQL's chosen plan and sort method. Returned rows are bounded by `q`, giving application result space proportional to (O(q(d + T̄))), where (T̄) is average returned passage text/metadata size.

A document filter can reduce the rows considered when PostgreSQL uses the
B-tree index on `document_id`; it does not guarantee a particular plan.
Without an approximate vector index, do not describe unfiltered vector search
as logarithmic-time retrieval.

### 7.7 Duplicate suppression

The retrieval service normalizes candidate text and checks a set of already
seen normalized strings.

- **Time:** expected (O`T_q`), where `T_q` is the total character count of the candidate texts normalized and hashed. The number of candidates is `q`, not the full corpus size.
- **Space:** (O`T_q`) for normalized keys and retained unique results.

For a fixed `top_k` of 5, the candidate request is 20; for larger limits the
candidate request is capped at 200 unless `top_k` itself exceeds 200.

## 8. Overall V1 complexity

There is no single useful complexity number for every operation: one-time
document ingestion and each online retrieval query have different costs.

### 8.1 Ingesting a document

Ignoring PDF-parser-specific behavior and database I/O, an approximate
combined model is:

```text
O\left(
P + S +
CA(L^2H + LH^2) +
C(d + \log M) +
S_p
\right)
```

where `S_p` is the text size in passages after chunking/overlap. Some terms
overlap in practice (for example, `S_p` is bounded by a constant-factor
multiple of `S` under the fixed V1 chunk configuration).

With fixed chunk parameters and fixed model/token-length bounds, this is
linear in document text/passages apart from database index-maintenance factors.
In most environments, Transformer inference and database writes are the
stages to profile first; measurements decide the real bottleneck.

Peak application memory is approximately:

```text
O\left(S + C(d + \bar{T}) + BL^2\right)
```

plus the model weights and runtime buffers, where (T̄) is average
passage text/provenance size. The implementation retains the extracted
document, passage list, and embedding results, so ingestion memory grows with
document size; it is not a streaming, constant-memory ingestion pipeline.

### 8.2 One retrieval query

For a query and an unfiltered corpus of `M` passages:

```text
O\left(
A(L_q^2H + L_qH^2) +
Md + M\log M + T_q
\right)
```

This combines query embedding, exact vector-distance evaluation and ranking,
and candidate deduplication. With the default model and fixed result limit,
the corpus-dependent term is dominated by the exact scan/ranking and grows
with `M`. The query embedding cost does not grow with corpus size.

Query working memory includes the model's activation memory, PostgreSQL's
plan-dependent sort/work memory, and the returned candidate text/results.
Persistent database storage is separate from per-query working memory.

### 8.3 Persistent database space

For `M` stored passages, embedding dimension `d`, and average stored
passage text size (T̄):

```text
O\left(M(d + \bar{T})\right)
```

This excludes indexes, tuple/page overhead, WAL, dead tuples pending vacuum,
metadata, and PostgreSQL's other storage overhead. With `d=384`, the vector
component per passage is fixed-size in the current configuration; text and
database overhead also contribute materially.

## 9. Practical complexity conclusion

| Operation | V1 growth characteristic | Main constraint |
|---|---|---|
| PDF extraction | Approximately linear in pages and extracted text | PDF structure and in-memory document handling |
| Chunking | Linear under fixed V1 chunk settings | Overlap duplication and character-based boundaries |
| Embedding all passages | Linear in passage count when model and sequence bound are fixed | Transformer computation and batch/model memory |
| Store/upsert | Per-row insertion/update plus index maintenance | Database I/O, transactions, index growth |
| Query embedding | Bounded for a single query under fixed model limits | Model load/resident memory and inference device |
| Exact vector search | Linear distance work in stored passage count; sorting adds cost | No ANN vector index |
| Duplicate suppression | Linear in candidate text inspected on average | Only deduplicates normalized literal text |

**Main V1 trade-off:** the system prioritizes simplicity, local execution,
traceability, and an exact-search correctness baseline. The main scaling
constraint is query-time exact vector search over a growing corpus, while the
main quality constraints are provisional evaluation judgments, text-only
ingestion, character-based chunking, and the absence of answer generation and
evidence-sufficiency checks.

## 10. Recommended work before claiming production readiness

1. Validate the eight-question relevance judgments and expand the benchmark across representative documents and questions.
2. Measure ingestion throughput, query latency, peak RAM, and PostgreSQL storage on a documented corpus size.
3. Add lexical/hybrid retrieval evaluation for exact identifiers and domain-specific terms.
4. Evaluate token-aware chunk sizes and the impact of the 256-word-piece truncation boundary.
5. If measured latency justifies it, evaluate HNSW or another approximate index against the exact-search baseline, including recall and latency regressions.
6. Implement and separately evaluate evidence sufficiency, conflicting-evidence handling, answer generation, and source citations before marketing the platform as end-to-end question answering.
7. Record model revision and preprocessing/configuration metadata when extending model management, and define a safe re-embedding/index migration procedure.

These are recommendations for future evaluation; they are not features claimed
to exist in V1.
