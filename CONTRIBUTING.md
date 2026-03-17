# Contributing

## Development setup

```bash
git clone https://github.com/Allium-Science/allium-cli.git
cd allium-cli
uv sync
```

Run the CLI locally:

```bash
uv run allium --help
```

### Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format --check .
```

## Release process

Releases are automated via GitHub Actions, triggered by git tags.

1. Bump `version` in `pyproject.toml` (e.g., `0.1.0` -> `0.2.0`)
2. Commit and push to `main`
3. Tag the release: `git tag cli.prod.v0.2.0 && git push origin cli.prod.v0.2.0`
4. The tag triggers the publish workflow which builds and uploads to PyPI

The workflow validates that the tag version matches `pyproject.toml` before publishing.
