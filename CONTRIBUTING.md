# Contributing to Cohezion

## Coding Standards

We strive to maintain high code quality and consistency. Please adhere to the following standards.

### Python

- **Style Guide**: We follow [PEP 8](https://peps.python.org/pep-0008/).
- **Formatter**: We use `black` (via `ruff format`) with a line length of 88.
- **Linter**: We use `ruff` for linting.
  - Ensure all code passes `ruff check .` before committing.
  - Imports should be sorted (handled by `ruff`).
- **Type Hinting**: Use type hints for all function arguments and return values.

### Markdown

- Use standard Markdown syntax.
- Ensure headers are properly nested.
- Use lists for structured data.

## Workflow

1.  Create a story in `docs/stories`.
2.  Run the `dev-story` workflow.
3.  Ensure all tests and checks pass.
4.  Submit for review.
