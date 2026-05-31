# Data Fetching Gotchas

## Query Key Mismatches (Server vs Client)
When prefetching on the server and using `useQuery` on the client, the query key
MUST be identical. If they differ by even one character, React Query treats them
as different queries → data is fetched twice, hydration breaks.

**Check:** Does the server prefetch use the exact same key factory function as
the client hook?

## Dehydration Strips Class Methods
`dehydrate()` serializes to JSON, which strips class instances to plain objects.
Never prefetch domain objects with business methods on the server.

**Wrong:** Prefetch `ProductDomain` (has `.isPhoenix()` method) → dehydrate → client receives plain object → `.isPhoenix()` is undefined.

**Right:** Prefetch raw API response → dehydrate → client uses `select` option in
`useQuery` to map to domain objects.

## Stale Data After SSR
Default `staleTime` is 0, meaning React Query immediately refetches after
hydration. Set `staleTime > 0` on the server `QueryClient` to prevent this.

## Forgetting Cache Invalidation After Mutation
After a `useMutation` succeeds, call `queryClient.invalidateQueries` with the
relevant key. Otherwise the UI shows stale data until manual refresh.

## Missing `enabled` Guard
If a query depends on a parameter that might be undefined (e.g., a selected ID),
use `enabled: !!id` to prevent the query from firing with undefined.

## Raw fetch/axios in Components
All HTTP calls go through the project's API instance (usually in `api/` or `lib/`).
Never import `fetch` or `axios` directly in a component or hook.
