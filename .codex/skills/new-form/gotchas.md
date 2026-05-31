# New Form Gotchas

## Not Reading Existing Forms First
The #1 mistake. Every project wires forms differently. Read an existing form
before writing anything.

## Missing Default Values
react-hook-form requires default values for every field. Undefined fields
cause silent validation failures and React warnings.

## Schema in Wrong Location
If the project puts schemas in `features/<name>/data/forms/formSchemas.ts`,
put yours there too. Don't create a new convention.

## Forgetting FormMessage
Without `<FormMessage />` inside each `<FormItem>`, validation errors exist
but are invisible to the user.

## No Loading State on Submit
Use `mutation.isPending` or `form.formState.isSubmitting` to disable the
submit button and show a loading indicator.
