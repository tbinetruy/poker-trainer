# React Patterns Gotchas

## "use client" Creep
Adding "use client" to a component makes its entire subtree client-rendered.
Push client boundaries to the smallest leaf components possible. A page or
layout should almost never be a client component.

**Wrong:** Making a page "use client" because it has one interactive button.
**Right:** Extract the button into a tiny client component, keep the page as server.

## useEffect for Data Fetching
Never fetch data in useEffect. Use:
- Server components: `async` function, `await` directly
- Client components: `useQuery` from TanStack React Query
- Mutations: `useMutation` from TanStack React Query

**Wrong:**
```tsx
const [data, setData] = useState(null);
useEffect(() => {
  fetch("/api/products").then(r => r.json()).then(setData);
}, []);
```

**Right:**
```tsx
const { data } = useQuery({ queryKey: ["products"], queryFn: fetchProducts });
```

## useEffect for Derived State
If a value can be computed from props or other state, compute it during render.

**Wrong:**
```tsx
const [fullName, setFullName] = useState("");
useEffect(() => { setFullName(`${first} ${last}`); }, [first, last]);
```

**Right:**
```tsx
const fullName = `${first} ${last}`;
```

## The useEffect Decision Tree

`useEffect` is a **last resort**, not a default tool. Before writing one, walk
this ladder top-to-bottom and stop at the first match:

1. **Derived value** — compute it during render.
2. **`useMemo` / `useCallback`** — if the derivation is expensive or needs a
   stable identity.
3. **Event handler** — if the logic only runs in response to user action.
4. **TanStack Query** (`useQuery` / `useMutation`) — all data fetching.
5. **`useState` initializer** — for one-time reads (`useState(() => ...)`) from
   `localStorage`, `sessionStorage`, URL params, etc.
6. **JSX attribute** — `autoFocus`, `defaultValue`, `defaultChecked`.
7. **Callback ref** — `ref={useCallback(node => { if (node) ... }, [])}` for
   DOM work on mount (portals, shadow DOM adoption, focus management tied to a
   specific element).
8. **Existing shared hook** — check `frontend/src/hooks/` first:
   `useEscapeKey`, `useKeyboardShortcut`, `useHasMounted`, `useIsMobile`,
   `useClickOutside`, `useScrollReveal`, `useBodyOverflowLock`,
   `useDebouncedValue`, `useOnMountMutation`, `useCountdownTimer`, etc.
9. **New custom hook** — if none of the above fit but the logic is
   reusable, write a new hook under `frontend/src/hooks/` or
   `frontend/src/features/<feature>/hooks/`.
10. **Last-resort inline `useEffect`** — only if the effect is single-use and
    cannot be meaningfully named.

See `references/useEffect-escape-hatches.md` for a table of concrete patterns
and their replacements.

## One useEffect Per Component — Hard Rule

**A component must not contain more than one `useEffect`.** Multiple effects
in a component body are a code smell — each represents a separate lifecycle
concern that deserves its own name.

The fix is always the same: extract the effect into a **dedicated custom hook**
named after what it does (`useCountdownTimer`, `useFocusAmbient`,
`usePersonaRotation`). Component bodies contain render + event handlers only.

**Wrong:**
```tsx
function WhatsAppModal({ open, onConnected }) {
  useEffect(() => { onConnectedRef.current = onConnected; }, [onConnected]);
  useEffect(() => { if (!open) abortRef.current?.abort(); }, [open]);
  useEffect(() => { if (open) resetState(); }, [open]);
  useEffect(() => {
    if (step !== "qr") return;
    const t = setInterval(() => setCountdown(c => c - 1), 1000);
    return () => clearInterval(t);
  }, [step]);
  // ...
}
```

**Right:**
```tsx
function WhatsAppModal({ open, onConnected }) {
  const { step, countdown, ... } = useWhatsAppSetupLifecycle({ open, onConnected });
  // pure render only
}
```

Hooks themselves may contain multiple effects only when the split is
load-bearing (distinct deps, distinct cleanup semantics, ordering contract).
Document the split in a JSDoc at the top of the hook. `useLocalStorage` is the
canonical documented exception.

## Effects Belong in Hooks, Not Components

Unavoidable effects must live in one of:

- **`frontend/src/hooks/`** — cross-feature reusable hooks.
- **`frontend/src/features/<feature>/hooks/`** — feature-scoped hooks.

Never in a component body. If you find yourself writing `useEffect` directly in
a `.tsx` component file, stop and extract it to a named hook first.

Cross-reference the `architecture-guard` skill for file-placement rules.

## Fat Page Components
Pages should be ~20 lines: fetch data, compose feature components. If a page
exceeds 50 lines, business logic is leaking into it.

## Component Over 120 Lines
If a component exceeds ~120 lines, it has multiple responsibilities. Extract
sections into sub-components, extract logic into hooks.
