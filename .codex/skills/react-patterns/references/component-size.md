# Component Size Rules

## Limits

- **Component total:** ~120 lines max (including imports)
- **JSX return:** ~50 lines max
- **Page components:** ~20-30 lines (thin wrappers)

## Decomposition Signals

Split a component when:
- It has more than one "section" (header, body, footer)
- It manages multiple pieces of unrelated state
- A chunk of JSX is repeated or could be reused
- You need a comment to explain what a section does (→ named component instead)

## Extraction Patterns

| What to extract | Where it goes |
|---|---|
| Repeated JSX block | Sub-component in same file or own file |
| Complex state logic | Custom hook |
| Data transformation | Utility function or computed value |
| Side effect logic | Custom hook with useQuery/useMutation |
