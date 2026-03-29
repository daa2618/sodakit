# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**sodakit** is a Python wrapper that builds on [sodapy](https://github.com/afeld/sodapy) to interact with the [Socrata Open Data API](https://dev.socrata.com/). It provides dataset discovery, searching, filtering by agency/tag/category, and data loading from multiple formats.

## Build & Development

- **Python**: 3.11+
- **Build system**: Poetry (poetry-core >= 2.0)
- **Install locally**: `pip install .` (or `poetry install`)
- **Linter**: `ruff` — run with `ruff check src/`
- **Tests**: `pytest` — run with `pytest tests/` or a single test with `pytest tests/test_client.py`
- **Virtual env**: `.venv` directory (already in .gitignore)

## Architecture

The package lives under `src/sodakit/` using the src-layout:

- **`api.py`** — Core classes. `MoreSocrata` handles connection to a Socrata domain and exposes metadata properties (ALL_AGENCIES, ALL_CATEGORIES, ALL_DOMAIN_TAGS, ALL_DATA_TYPES, ALL_DATASET_NAMES). `MoreSocrataData` extends it with dataset loading (`try_loading_dataset`), querying (`query_dataset`), searching, and filtering by agency/tag/type.
- **`exceptions.py`** — `DatasetNotFound`, `OrganizationNotFound`.
- **`utils/response.py`** — HTTP wrapper (`Response`, `GET_RESPONSE`, `POST_RESPONSE`) around `requests` with retry and JSON extraction.
- **`utils/data_loader.py`** — `Dataset` class loads data from URLs or file paths, auto-detecting format (CSV, Excel, ODS, JSON, PDF, GeoJSON, text). Has special handling for GitHub raw URLs. `PostProcess` provides DataFrame column manipulation helpers.
- **`utils/data_version.py`** — `FileVersion` manages date-stamped file versioning in a local `data/` directory. Used by `MoreSocrata` to cache API responses to disk.
- **`utils/data_writer.py`** — `WriteFile` extends `FileVersion` to write data (JSON, CSV, PDF, text, Excel) to disk.
- **`utils/strings.py`** — String matching using `SequenceMatcher` and NLTK `SnowballStemmer` for fuzzy dataset/agency search.
- **`utils/log_helper.py`** — `BasicLogger` wrapping stdlib `logging`.

## Key Patterns

- `MoreSocrata` lazily loads and caches all domain datasets to a local JSON file (via `FileVersion.load_latest_file`). The cache lives under `data/<domain_id>/`.
- Credentials can be passed directly or loaded from environment variables (`APP_TOKEN`, `USERNAME`, `PASSWORD`) via `dotenv`.
- Dataset search uses NLTK stemming first, then falls back to `SequenceMatcher` ratio >= 0.5.
- The old package layout (`sodakit/`) at the repo root is deleted; the active code is in `src/sodakit/`.

## Logging Protocol
Always follow the agent logging protocol defined in ~/.claude/skills/agent_logger/SKILL.md before and after every task.

Follow the agent_logger skill for this session.