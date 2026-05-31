---
name: react-patterns
description: Use when creating or reviewing React components, deciding between server and client components, or when tempted to use useEffect. Triggers on any React component creation, hook authoring, or component review.
---

# React Patterns

Codex already knows standard React — this skill exists to correct the mistakes
it keeps making anyway. Start with `gotchas.md` on every component creation or review.

## shadcn/ui First

Before building any UI element (button, input, card, dialog, table, select…),
check if the project has shadcn installed (`components.json` at root) and if
the component already exists in `src/components/ui/`. Use it instead of raw HTML.

- Use `cn()` for class merging — never template literals for conditional classes
- Use component variants (props) over arbitrary Tailwind overrides
- Use Lucide React for icons — don't mix icon libraries
- Form components must follow: `FormField` → `FormItem` → `FormLabel` + `FormControl` + `FormMessage`
- If a component isn't installed yet: `npx shadcn@latest add <component>`

See `references/` for project-specific rules on server-vs-client boundaries,
component size thresholds, and performance patterns. Before writing any
`useEffect`, consult `references/useEffect-escape-hatches.md`.
