---
name: new-page
description: Use when creating a new page, route, or view in a React routing project. Triggers on "new page", "add route", "create page for X". Scaffolds pages matching the project's existing data fetching and layout patterns.
---

# New Page Scaffold

Creates a new React page/route by reading existing pages to detect the project's pattern.

## Workflow

1. **Read existing pages**: Look at 2-3 page/route files to detect:
   - Do they prefetch data? (server-side `queryClient.prefetchQuery`)
   - Do they use `HydrationBoundary`?
   - Do they import from `features/`?
   - Is there a layout pattern to follow?
2. **Determine the page's needs**: Static? Dynamic? Data-driven?
3. **Scaffold page.tsx**: Match the detected pattern exactly.
4. **Create client component** if needed (for interactive parts).
5. **Add to navigation** if the project has a nav config.

## Rules

- Pages are ALWAYS server components — never add "use client".
- Pages should be thin (~20-30 lines) — delegate to feature components.
- If the project prefetches data, include the full prefetch → dehydrate → HydrationBoundary pattern.
- Dynamic routes use `[param]` folder naming.
- Match the metadata pattern from existing pages.

See `gotchas.md` for common mistakes.
