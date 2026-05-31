# Performance Rules (Critical Only)

Only the rules that cause real, measurable problems. Not micro-optimizations.

## Eliminate Fetch Waterfalls
Don't fetch sequentially when you can fetch in parallel.

**Wrong:**
```tsx
const user = await fetchUser(id);
const posts = await fetchPosts(user.id); // waits for user first
```

**Right (when independent):**
```tsx
const [user, posts] = await Promise.all([fetchUser(id), fetchPosts(id)]);
```

## Avoid Barrel Import Bloat
Importing from a barrel file (`index.ts`) can pull in the entire module.
Import specific files when tree-shaking doesn't help.

## Lazy Load Heavy Components
Use `dynamic()` or `React.lazy()` for components that are large or rarely visible
(modals, charts, admin panels).

## Don't Forget `key` on Lists
Missing or non-unique `key` props cause full list re-renders.
Use stable IDs, never array indices (unless the list is truly static).

## Memoize Expensive Computations
Use `useMemo` only for genuinely expensive operations (>1ms). Don't memoize
string concatenation or simple lookups.
