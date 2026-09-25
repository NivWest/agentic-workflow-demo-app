# Agent Guidelines

> These rules are loaded automatically by AI coding agents (Jules, Gemini, etc.)
> when they work on this repository. They define the project's coding standards,
> architecture constraints, and collaboration conventions.

---

## Project Overview

This is a **multi-agent FastAPI microservice** built with Python 3.11+,
Domain-Driven Design (DDD), and Hexagonal Architecture, deployed to
Google Cloud Run.

Before writing or modifying any code, **read and follow** the architecture
skill at [`.agents/skills/fastapi-multiagent-microservice/SKILL.md`](.agents/skills/fastapi-multiagent-microservice/SKILL.md).

---

## Architecture Rules (Mandatory)

1. **Always consult the skill first.** The
   `fastapi-multiagent-microservice` skill defines the canonical directory
   structure, layer boundaries, and dependency direction. Every import you
   write must satisfy the boundary table in that skill.

2. **Reference files are available.** If you need code examples for API
   patterns, telemetry, configuration, or Dockerfiles, read the
   corresponding files in the skill's `references/` and `examples/`
   directories — do not invent patterns from scratch.

3. **Do not skip the validation checklist.** Before finalizing your work,
   run through the checklist at the bottom of `SKILL.md`.

---

## Git Conventions

### Branch Naming

Use the pattern `{type}/{issue-number}-{short-kebab-description}`:

```
feat/42-add-summarizer-agent
fix/87-async-session-leak
chore/91-upgrade-pydantic-v2
refactor/103-extract-registry-pattern
```

### Commit Messages — Conventional Commits

Every commit **must** follow the
[Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<optional-scope>): <description>

[optional body]

[optional footer(s)]
```

**Allowed types:**

| Type         | When to Use                                              |
| :----------- | :------------------------------------------------------- |
| `feat`       | A new feature or capability                              |
| `fix`        | A bug fix                                                |
| `refactor`   | Code change that neither fixes a bug nor adds a feature  |
| `chore`      | Maintenance tasks (deps, configs, tooling)               |
| `style`      | Formatting, whitespace, linting (no logic change)        |
| `docs`       | Documentation only                                       |
| `test`       | Adding or updating tests                                 |
| `ci`         | CI/CD pipeline changes                                   |
| `perf`       | Performance improvement                                  |

### Commit Size & Planning

- **Plan before coding.** Break the implementation into a sequence of small,
  atomic commits. Each commit should represent one logical change.
- **Target 100–200 lines of diff per commit.** Smaller commits are easier
  to review, bisect, and revert.
- **Each commit must compile and pass tests.** Never leave the tree in a
  broken state between commits.
- **Order commits logically:**
  1. Models / schemas first
  2. Repository / service layer
  3. Domain logic / agents
  4. API routes
  5. Tests
  6. Documentation

---

## Code Quality Standards

| Standard       | Requirement                                                       |
| :------------- | :---------------------------------------------------------------- |
| Type hints     | Full annotations. Must pass `mypy --strict`.                      |
| Async I/O      | 100% async. No `requests`, `time.sleep`, or blocking calls.       |
| Logging        | `structlog` only. Never `import logging`.                         |
| Config         | `BaseSettings` + `Field(default=..., description=...)`.           |
| Lifespan       | `@asynccontextmanager`. Never `@app.on_event()`.                  |
| Dependencies   | Inject via `Depends()`. Wire in `api/dependencies.py`.            |
| Docstrings     | Google-style docstrings on all public classes and functions.       |
| Tests          | Write tests for every new public function. Mirror `src/` layout.  |

---

## Pull Request Guidelines

### PR Title

```
<type>(<scope>): <short-description> (#<issue-number>)
```

Example: `feat(agents): add summarizer workflow (#42)`

### PR Description Template

Every PR must include:

1. **Summary** — What was done and why (1–3 sentences).
2. **Linked Issue** — `Closes #<issue-number>`.
3. **Changes** — Bulleted list grouped by commit, explaining the "what" and
   "why" (not the "how" — the diff shows that).
4. **Testing** — How the changes were verified.
5. **Checklist** — Paste and check off the validation checklist from
   `SKILL.md`.

### Self-Review Comments

After opening the PR, add **inline review comments** on your own code to
explain non-obvious decisions, trade-offs, or areas where you'd like
reviewer attention. This helps the human reviewer focus.

---

## Review Feedback Response Protocol

When a human reviewer leaves comments on your PR:

1. **Read every comment** before making any changes. Understand the full
   picture of the feedback.
2. **Acknowledge each comment** with a reply — either explaining what you
   changed or respectfully discussing alternatives if you disagree.
3. **Make focused fix commits** for each piece of feedback. Use the format:
   ```
   fix(review): address <reviewer>'s feedback on <topic>
   ```
4. **Do not force-push or squash** during review. Reviewers need to see
   incremental fixes against their original comments.
5. **Re-request review** once all comments are addressed. Summarize what
   was changed in a final PR comment.
6. **Resolve conversations** only after the reviewer approves the resolution —
   never resolve your own threads.

---

## Security & Secrets

- Never commit secrets, API keys, or credentials.
- Use GitHub Secrets and inject via environment variables.
- Use `.env.example` (never `.env`) to document required variables.
- Validate all external input at the API boundary (Pydantic schemas).

---

## Dependencies

- Pin all dependencies in `requirements.lock`.
- Use `requirements.in` for human-readable source-of-truth.
- Prefer well-maintained, async-native libraries.
- Run `pip-compile` (or equivalent) to regenerate the lock file.

