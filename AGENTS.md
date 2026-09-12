# Agent Instructions

## Project

This repository contains a data engineering project based on
Wrocław bike-sharing data from Nextbike GBFS and Wrocław Open Data.

The project is designed as a realistic end-to-end data platform,
starting locally and potentially evolving toward cloud architecture.

## Architecture Principles

- Prefer simple solutions over unnecessary complexity.
- Do not introduce technologies without a concrete reason.
- Preserve raw source data.
- Separate ingestion, storage, transformation and presentation.
- Do not silently change data schemas.
- Do not invent data.
- Prefer reproducible pipelines.
- Design for incremental processing where appropriate.

## Python

- Use Python 3.x.
- Use uv for dependency management.
- Use type hints.
- Follow PEP 8.
- Use Ruff for linting and formatting.
- Use pytest for tests.
- Keep modules focused and small.

## Data Engineering

- Always explicitly define the grain of a dataset/table.
- Store timestamps consistently.
- Keep source data separate from transformed data.
- Prefer append-only ingestion for snapshots.
- Make ingestion idempotent where practical.
- Handle API failures explicitly.
- Never silently drop malformed records.
- Data quality checks must be added where appropriate.

## Task Management

Before starting work:
1. Read AGENTS.md.
2. Read ROADMAP.md
3. Read relevant documentation in docs/.
4. Read tasks/CURRENT.md.
5. Understand existing architecture and decisions.

During work:
- Work only on the current task unless a dependency requires otherwise.
- If a new required task is discovered, add it to CURRENT.md.
- Do not silently change architectural decisions.
- If an architectural change is required, document it as a proposed decision.

After work:
1. Run relevant tests.
2. Run linting/formatting.
3. Update documentation if behavior changed.
4. Update tasks/CURRENT.md.
5. Summarize what was changed and what remains.

## Git

- `main` is the stable branch and must remain working and tested.
- Do not implement features directly on `main`.
- Implement each meaningful bounded task on a dedicated focused branch, using
  names such as `feature/raw-quality-checks`, `feature/silver-layer`,
  `feature/gold-model`, or `feature/power-bi-model`.
- Before starting implementation, create or switch to the appropriate feature
  branch. Do not push directly to `main`.
- Commit bounded work with clear, meaningful commit messages.
- Before considering a task complete, run the relevant tests, run Ruff, verify
  the affected pipeline or command, inspect `git diff`, and confirm that no
  generated data, secrets, temporary files, or unrelated changes are included.
- Do not merge branches automatically. The human reviews and merges the PR
  into `main`.
- For completed bounded tasks, report the current branch, commits made, files
  changed, tests and checks passed, a recommended PR title and summary, and
  any concerns before merging.
- Never commit secrets.
- Never commit .env files.
- Never commit generated datasets unless explicitly requested.
- Keep commits focused.
- Do not rewrite history unless explicitly requested.

## Decision Making

The agent may make implementation-level decisions.

The agent must not make major architectural changes without documenting
the proposed change and explaining the trade-offs.

When requirements are ambiguous, prefer the simplest implementation
consistent with the documented architecture.