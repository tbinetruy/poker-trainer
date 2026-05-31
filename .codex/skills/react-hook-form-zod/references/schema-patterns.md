# Zod Schema Patterns

## Basic

```ts
const schema = z.object({
  name: z.string().min(1, "Required"),
  email: z.string().email("Invalid email"),
  age: z.coerce.number().min(0).max(150), // coerce string → number
  role: z.enum(["admin", "user", "guest"]),
  bio: z.string().optional(),
});

type FormData = z.infer<typeof schema>;
```

## Optional with Default

```ts
z.string().default("")     // always has a value
z.string().optional()      // can be undefined
z.string().nullable()      // can be null
```

## Discriminated Union (conditional fields)

```ts
const schema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("email"), email: z.string().email() }),
  z.object({ type: z.literal("phone"), phone: z.string().min(10) }),
]);
```

## Transform (clean input)

```ts
z.string().trim().toLowerCase()
z.string().transform((val) => val.replace(/\s+/g, "-")) // slugify
```

## Where to Put Schemas

Check the project convention. Common patterns:
- `features/<name>/data/forms/formSchemas.ts`
- `features/<name>/schemas.ts`
- Colocated next to the form component

Match whatever the project already does.
