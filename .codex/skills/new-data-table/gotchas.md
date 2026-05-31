# New Data Table Gotchas

## Building a Custom Table When a Wrapper Exists
Check `components/` for a shared DataTable before building from scratch.
Most projects have one.

## Column Accessors Don't Match API Fields
The `accessorKey` in column definitions must match the exact field name from
the API response. Typos cause silent undefined values.

## Server-Side Sort Parameter Format
Different backends expect different sort formats:
- `-field` (Django REST: prefix with `-` for descending)
- `field:desc` (others)
- `sort=field&order=desc` (query params)

Check existing sort implementations to match.

## Pagination Query Key Must Include Page Params
If pagination params aren't in the query key, changing pages shows cached data
from the previous page.

```tsx
// Include page in query key
queryKey: queryKeys.products.list({ page, pageSize, sort })
```

## Missing Loading Skeleton
Tables without loading states show a jarring empty → full transition.
Add a skeleton or loading spinner.
