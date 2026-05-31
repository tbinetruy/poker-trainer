# Server vs Client Components

## Decision Tree

Start at "Server Component" and only switch to client if one of these is true:

1. Uses hooks (`useState`, `useEffect`, `useQuery`, custom hooks with state)
2. Uses event handlers (`onClick`, `onChange`, `onSubmit`)
3. Uses browser APIs (`window`, `document`, `localStorage`)
4. Uses React context that requires client rendering

If none of these apply → keep it as a server component.

## Rules

- Pages (`page.tsx`) and layouts (`layout.tsx`) are ALWAYS server components
- `"use client"` must be the first line, before any imports
- Server components can `await` async operations directly
- Server components can import client components (but not vice versa)
- For mixed pages: server component wraps client component via children/props

## Composition Pattern

```tsx
// page.tsx (server)
export default async function ProductPage() {
  const data = await fetchProducts(); // server-side data fetch
  return <ProductList initialData={data} />; // pass to client
}

// ProductList.tsx (client — needs interactivity)
"use client";
export function ProductList({ initialData }) {
  const [filter, setFilter] = useState("");
  // ...interactive logic
}
```
