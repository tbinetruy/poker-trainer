# Server-Side Prefetching

## The Pattern

```tsx
// page.tsx (server component)
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

export default async function Page() {
  const queryClient = getQueryClient(); // per-request singleton via React.cache()
  const api = await getServerApi();      // server-side API with auth from cookies

  await queryClient.prefetchQuery({
    queryKey: queryKeys.products.list(),  // MUST match client exactly
    queryFn: () => api.products.list(),
  });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ClientComponent />
    </HydrationBoundary>
  );
}
```

## Checklist

- [ ] `getQueryClient()` uses `React.cache()` for per-request singleton
- [ ] Server QueryClient has `staleTime > 0` (e.g., 60_000) to prevent immediate refetch
- [ ] Query key in prefetch matches client `useQuery` exactly (use same factory)
- [ ] Prefetch raw API data, NOT domain objects (dehydrate strips methods)
- [ ] Server API reads auth from cookies (not sessionStorage)
