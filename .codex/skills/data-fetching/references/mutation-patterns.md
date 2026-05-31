# Mutation Patterns

## useMutation Pattern

```tsx
const mutation = useMutation({
  mutationFn: (data: CreateProductInput) => api.products.create(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.products.all });
    toast.success("Product created");
  },
  onError: (error) => {
    toast.error("Failed to create product");
  },
});
```

## Rules

- Always invalidate related queries on success
- Use `queryKeys.*.all` for broad invalidation (any product query)
- Use specific keys for targeted invalidation
- Show user feedback (toast) on success and error
- Don't manually update cache unless optimistic updates are needed
