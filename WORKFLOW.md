# Issue Workflow

## Triage
Issues are triaged by maintainers using template completeness and labels.

Suggested labels:
- `type::bug`, `type::feature`, `type::ux`, `type::security`
- `priority::high|medium|low`
- `severity::blocking|major|minor|cosmetic`
- `status::needs-triage|needs-info|accepted|in-progress|done`
- `area::<component>`

## Development
Once an issue is accepted, it is assigned and moved to `status::in-progress`.

## Completion
When resolved, the issue is moved to `status::done`, linked to implementing merge requests, and closed with resolution notes.
