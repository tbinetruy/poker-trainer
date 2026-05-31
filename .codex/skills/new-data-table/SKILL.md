---
name: new-data-table
description: Use when creating a new data table, list view, or tabular display with sorting and pagination. Triggers on "new table", "add data table", "create list for X", or when the task involves displaying collections of records.
---

# New Data Table Scaffold

Creates a data table by detecting the project's existing table patterns.

## Workflow

1. **Find existing tables**: Search for `useReactTable`, `DataTable`, `ColumnDef` in the codebase.
2. **Detect shared wrapper**: Check if the project has a reusable `DataTable` component.
3. **Check sorting pattern**: Server-side (query params) or client-side?
4. **Check pagination pattern**: Server-side or client-side? Custom component?
5. **Define columns**: Create column definitions matching existing tables.
6. **Create query hook**: Data fetching with React Query, including sort/pagination params.
7. **Compose**: Wire columns + data + table + pagination.

## Rules

- If a shared `DataTable` wrapper exists, use it. Don't build a new one.
- Match column definition style from existing tables.
- Server-side sorting needs param conversion (e.g., `-field` for descending).
- Include loading and empty states.
- Use the project's pagination component.

See `gotchas.md` for common mistakes.
