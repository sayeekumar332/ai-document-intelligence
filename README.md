# AI Document Intelligence Platform

A local-first AI application that answers questions about PDF documents
using retrieved evidence, source citations, and explicit handling of
insufficient or conflicting evidence.

## Project goals

- Extract text from PDF documents.
- Split extracted text into searchable chunks.
- Retrieve relevant passages for a user's question.
- Generate answers grounded in retrieved evidence.
- Display source references for answers.
- Identify questions that the available documents cannot answer.
- Evaluate retrieval and answer quality with a repeatable test dataset.
- Provide a Python API and a simple user interface.

## Engineering principles

- Run locally without paid AI APIs or paid hosting.
- Keep document processing, retrieval, generation, and evaluation modular.
- Test failure cases, not only successful examples.
- Track code changes with Git.
- Document setup instructions and known limitations.

## Status

Project setup in progress. Features will be implemented and tested
incrementally.
