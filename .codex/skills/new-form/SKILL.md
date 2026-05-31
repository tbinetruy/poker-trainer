---
name: new-form
description: Use when creating a new form with validation, adding form fields, or building a form-driven UI. Triggers on "new form", "add form", "create form for X", or when the task involves user input with validation.
---

# New Form Scaffold

Creates a form by reading existing forms in the project to detect the validation
library, UI library, and file organization pattern.

## Workflow

1. **Detect form stack**: Search for `useForm`, `zodResolver`, `FormField` in the codebase.
   Identify: which validation library (Zod? Yup?), which UI (shadcn? MUI?), which form lib (RHF?).
2. **Find schema location**: Search for existing schema files to detect where they live
   (e.g., `features/*/data/forms/`).
3. **Create schema**: Define the Zod schema matching the form's requirements.
4. **Create form component**: Wire RHF + Zod + UI components following existing patterns.
5. **Add mutation**: If the form submits data, create a `useMutation` hook.
6. **Verify**: Check that form validates, submits, and shows errors correctly.

## Rules

- ALWAYS read existing forms first — match the project's pattern exactly.
- Schema and component may be in separate files — check project convention.
- Include proper error messages in the schema.
- Wire toast notifications for success/error (if the project uses them).
- Use the project's mutation pattern for form submission.

See `gotchas.md` for common mistakes.
