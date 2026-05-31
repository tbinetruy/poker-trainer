# New Page Gotchas

## Making the Page a Client Component
Pages should almost never be "use client". If you need interactivity,
create a separate client component and compose it in the server page.

## Forgetting Metadata
Every page should export metadata (title, description) for SEO.
Check existing pages for the metadata pattern used.

## Skipping the Prefetch Pattern
If the project uses server-side prefetching, skipping it causes:
- Flash of loading state on first visit
- Slower perceived performance
- SEO issues (content not in initial HTML)

## Dynamic Route Without generateStaticParams
If the route is `[id]`, consider whether the set of IDs is known at build time.
If so, add `generateStaticParams` for static generation.

## Forgetting to Update Navigation
Check if the project has a navigation config file (e.g., `data/navigation.ts`)
and add the new page to it.
