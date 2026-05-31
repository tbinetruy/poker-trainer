# useEffect Escape Hatches

Before writing a `useEffect`, find your pattern in this table. Most inline
effects can be replaced with something simpler.

| Pattern you see | Replace with | Why |
|---|---|---|
| Fetching data | `useQuery` (TanStack) | Handles caching, refetch, stale-while-revalidate, error states. Never fetch in an effect. |
| Mutation on mount | `useOnMountMutation(mutation, vars)` | Fired-ref guards against StrictMode double-fire; intent is clear. |
| `fullName = first + last` in state | Compute during render | No state sync needed. |
| Reading `localStorage` / `sessionStorage` on mount | Lazy `useState(() => read())` initializer | Runs once, before first paint, no effect lifecycle. |
| Focus an input on mount | `autoFocus` attribute | Browser-native behavior, zero JS. |
| Setting `defaultValue` on mount | `defaultValue` / `defaultChecked` attribute | Same. |
| Logging to Sentry when a prop arrives | Inline call during render guarded by `useRef` fired-flag, or an error boundary `onError` | Effects are not error boundaries. |
| Debouncing a value | `useDebouncedValue(value, ms)` | Named, testable, reusable. |
| Debouncing a callback | `useDebouncedCallback(fn, ms)` | Same. |
| Resetting child state when a key changes | `key={changingValue}` on the child | React remounts on key change — no effect needed. |
| Shadow DOM adoption / portal attach | Callback ref: `ref={useCallback(node => {...}, [])}` | Runs synchronously when the node mounts; no effect latency. |
| Escape-key listener | `useEscapeKey(onClose)` | Existing shared hook. |
| Arbitrary keyboard shortcut | `useKeyboardShortcut(key, handler)` | Existing shared hook. |
| SSR guard (render only after mount) | `useHasMounted()` | Existing shared hook. |
| Media-query observation | `useIsMobile()` | Existing shared hook. |
| Outside click / dismiss | `useClickOutside(ref, onClose)` | Existing shared hook. |
| IntersectionObserver for reveal | `useScrollReveal()` | Existing shared hook. |
| Lock body scroll in modal | `useBodyOverflowLock(open)` | Existing shared hook. |
| Mirror a prop into a ref | Assign `ref.current = prop` during render | Refs are mutable containers, not reactive state. React allows this. |
| Derived "advance on external state change" (e.g. step = connected ? "done" : "wait") | Compute during render from props | Keep state minimal; derive the rest. |
| Timer that runs while some condition holds | `useCountdownTimer({ enabled, ... })` or a dedicated hook | Name the timer's purpose. |
| Scroll-to-top on mount | `useResetScrollOnMount()` | One-liner shared hook. |
| CSS-var sync on theme change | `useThemeCSSVarSync(vars, onApply)` | Feature-local hook. |
| Mouse tracking with RAF | A dedicated hook (`useMouseGlowTracking`, `useDraggable`) | Never in a component body. |

## Documented exception: `useLocalStorage`

`frontend/src/hooks/useLocalStorage.ts` contains three `useEffect` calls
(hydrate from storage, debounced persist, unmount cleanup). They cannot be
safely merged — the hydration flag guards the persist effect to prevent a
write-on-mount, and cleanup has different deps. This is the canonical
exception. Any new hook that wants to claim an exception must have an explicit
JSDoc justification and a reviewer sign-off.

## See also

- `gotchas.md` — the decision tree and one-effect-per-component rule.
- `references/performance.md` — when to memoize.
- `references/server-vs-client.md` — move logic out of client components entirely when possible.
