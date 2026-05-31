# Codex Skills

This directory contains project-specific skills that provide Codex with domain knowledge and best practices for this Django codebase.

## Skills by Category

### Meta & Development Tools
| Skill | Description |
|-------|-------------|
| [skill-creator](./skill-creator/SKILL.md) | Guide for creating effective skills that extend Codex's capabilities |
| [django-extensions](./django-extensions/SKILL.md) | Django-extensions management commands for introspection, debugging, and development |

### Workflows
| Skill | Description |
|-------|-------------|
| [onboard](./onboard/SKILL.md) | Onboard Codex to a new task by exploring the codebase and building context |
| [ticket](./ticket/SKILL.md) | Work on a JIRA/Linear ticket end-to-end |
| [pr-review](./pr-review/SKILL.md) | Review a pull request using project standards |
| [pr-summary](./pr-summary/SKILL.md) | Generate a pull request summary for the current branch |
| [code-quality](./code-quality/SKILL.md) | Run code quality checks and report findings by severity |
| [docs-sync](./docs-sync/SKILL.md) | Check if documentation is in sync with code |
| [worktree-commit-merge](./worktree-commit-merge/SKILL.md) | Commit worktree changes, merge into master/main, sync branch |

### Testing & Debugging
| Skill | Description |
|-------|-------------|
| [pytest-django-patterns](./pytest-django-patterns/SKILL.md) | pytest-django, Factory Boy, fixtures, TDD workflow |
| [systematic-debugging](./systematic-debugging/SKILL.md) | Four-phase debugging methodology, root cause analysis |

### Django Core
| Skill | Description |
|-------|-------------|
| [django-models](./django-models/SKILL.md) | Model design, QuerySet optimization, signals, migrations |
| [django-forms](./django-forms/SKILL.md) | Form handling, validation, ModelForm patterns |
| [django-templates](./django-templates/SKILL.md) | Template inheritance, tags, filters, partials |

### Frontend & UI
| Skill | Description |
|-------|-------------|
| [react-patterns](./react-patterns/SKILL.md) | React component structure, hooks, shadcn/ui usage |
| [data-fetching](./data-fetching/SKILL.md) | Query/mutation patterns and cache consistency |
| [react-hook-form-zod](./react-hook-form-zod/SKILL.md) | Form validation with react-hook-form and Zod |
| [new-page](./new-page/SKILL.md) | Page/route scaffolding that follows existing frontend patterns |
| [new-form](./new-form/SKILL.md) | Form scaffolding that follows existing frontend patterns |
| [new-data-table](./new-data-table/SKILL.md) | Table/list scaffolding with sorting and pagination |
| [frontend-design](./frontend-design/SKILL.md) | Production-grade frontend design guidance |
| [htmx-patterns](./htmx-patterns/SKILL.md) | Imported Django/HTMX reference; use only if the project explicitly adds HTMX |

### Background Tasks
| Skill | Description |
|-------|-------------|
| [celery-patterns](./celery-patterns/SKILL.md) | Celery tasks, retry strategies, periodic tasks |

## Skill Combinations for Common Tasks

### Building a New Feature
1. **django-models** - Design models
2. **pytest-django-patterns** - Write backend tests (TDD)
3. **react-patterns** - Build React UI with shadcn/ui when possible
4. **data-fetching** - Wire frontend queries and mutations
5. **react-hook-form-zod** - Add validated forms when needed

### Building a Background Task
1. **celery-patterns** - Task definition
2. **django-models** - Database operations
3. **pytest-django-patterns** - Task tests

### Debugging an Issue
1. **systematic-debugging** - Root cause analysis
2. **pytest-django-patterns** - Write failing test first
3. **django-extensions** - Use show_urls, list_model_info, shell_plus for investigation

### Creating New Skills
1. **skill-creator** - Follow the skill creation guide
2. **django-extensions** - Test your skill with project introspection commands

## How Skills Work

Skills are automatically invoked when Codex recognizes relevant context. Each skill provides:

- **When to Use** - Trigger conditions
- **Core Patterns** - Best practices and examples
- **Anti-Patterns** - What to avoid
- **Integration** - How skills connect

## Adding New Skills

1. Create directory: `.codex/skills/skill-name/`
2. Add `SKILL.md` (case-sensitive) with YAML frontmatter:
   ```yaml
   ---
   # Required fields
   name: skill-name              # Lowercase, hyphens, max 64 chars
   description: What it does and when to use it. Include trigger keywords.  # Max 1024 chars

   ---
   ```
3. Include standard sections: When to Use, Core Patterns, Anti-Patterns, Integration
4. Add to this README

**Important:** The `description` field is critical—Codex uses semantic matching on it to decide when to apply the skill. Include keywords users would naturally mention.

## Maintenance

- Update skills when patterns change
- Remove outdated information
- Add new patterns as they emerge
- Keep examples current with codebase
