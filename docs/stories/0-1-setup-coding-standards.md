# Story 0.1: Setup Coding Standards

Status: review

## Story

As a Developer,
I want to establish coding standards and linting rules,
so that the codebase remains consistent and maintainable.

## Acceptance Criteria

1. Define coding standards for Python (PEP8 based).
2. Define coding standards for Markdown.
3. Configure a linter (e.g., `ruff` or `pylint`) to enforce these standards.
4. Create a `CONTRIBUTING.md` or update it with these standards.

## Tasks / Subtasks

- [x] Research best practices for Python and Markdown linting (AC: 1, 2)
- [x] Create/Update `pyproject.toml` with linter configuration (AC: 3)
- [x] Create/Update `CONTRIBUTING.md` with coding standards (AC: 4)
- [x] Run linter on existing code and fix violations (AC: 3)

## Dev Notes

- Use `ruff` for Python linting as it's fast and comprehensive.
- Use `markdownlint` for Markdown if possible, or just standard guidelines.

### Project Structure Notes

- Ensure config is at the root.

### References

- [PEP 8](https://peps.python.org/pep-0008/)

## Dev Agent Record

### Context Reference

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
