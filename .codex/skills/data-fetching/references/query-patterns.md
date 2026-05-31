# Query Patterns

## Query Key Factory

Every project should have a centralized key factory. Find it (usually in
`api/queryKeys.ts` or similar) and use it.

```ts
// Pattern:
export const queryKeys = {
  products: {
    all: ["products"] as const,
    list: (params?: Filters) => ["products", "list", params] as const,
    detail: (id: string) => ["products", id] as const,
  },
};
```

## useQuery Pattern

```tsx
const { data, isLoading, error } = useQuery({
  queryKey: queryKeys.products.list(filters),
  queryFn: () => api.products.list(filters),
  enabled: !!requiredParam,       // guard if needed
  select: (raw) => mapToDomain(raw), // transform if needed
});
```

## Rules

- `queryFn` calls the API instance, never raw fetch
- `queryKey` uses the factory, never inline arrays
- `enabled` guards queries that depend on optional params
- `select` transforms raw API data to domain objects (runs on client, cached data stays raw)
