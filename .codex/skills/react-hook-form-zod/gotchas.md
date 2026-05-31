# React Hook Form + Zod Gotchas

## Missing zodResolver
The most common mistake. Without it, Zod validation doesn't run.

```tsx
import { zodResolver } from "@hookform/resolvers/zod";

const form = useForm<z.infer<typeof schema>>({
  resolver: zodResolver(schema), // REQUIRED
  defaultValues: { ... },
});
```

## Default Values Must Match Schema Shape
Every field in the schema needs a default value, and the shape must match.
Missing defaults cause `undefined` values that fail validation silently.

## FormField render Prop
The `render` prop gives you `{ field }` — spread it onto the input.

```tsx
<FormField
  control={form.control}
  name="email"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Email</FormLabel>
      <FormControl>
        <Input {...field} />  {/* spread field here */}
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

## File Inputs Don't Work Controlled
File inputs can't be controlled by react-hook-form. Use `register` with a ref,
or handle via `onChange` manually.

## Array Fields
For dynamic field arrays, use `useFieldArray` — don't manage array state manually.

## Async Validation
Use Zod's `.refine()` with an async function for server-side validation
(e.g., checking if email already exists).

```ts
const schema = z.object({
  email: z.string().email().refine(
    async (email) => !(await checkEmailExists(email)),
    "Email already in use"
  ),
});
```
