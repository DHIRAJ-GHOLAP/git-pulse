# Contributing to git-pulse

Thank you for your interest in contributing to `git-pulse`! We welcome contributions from developers of all skill levels.

## Code of Conduct

Please treat everyone with respect, kindness, and professionalism.

## Getting Started

1. **Fork the Repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<your-username>/git-pulse.git
   cd git-pulse
   ```
3. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

We use `pytest` for all unit and integration tests:

```bash
pytest
```

To run with coverage:
```bash
pytest --cov=git_pulse
```

### Commit Guidelines

We adhere strictly to [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add new CLI command for stash diffs`
- `fix: resolve division by zero in heatmap when zero commits exist`
- `docs: update quickstart instructions in README`
- `perf: optimize git log subprocess parser`
- `refactor: extract terminal formatting into views helper`

This enables automatic changelog generation using `git-pulse changelog`!

## Submitting Pull Requests

1. Create a descriptive branch:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Write tests covering your changes.
3. Verify that all tests pass (`pytest`).
4. Push your branch and open a Pull Request against `main`.
