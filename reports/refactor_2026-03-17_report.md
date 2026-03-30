# TypeScript Refactoring Report

**Date:** 2026-03-17  
**Scope:** Inline JavaScript → TypeScript (`typescript/src/main.ts`)  
**Author:** GitHub Copilot

---

## Summary

All inline `<script>` blocks containing DOM-manipulation JavaScript were identified across the Jinja2 HTML templates, refactored into typed TypeScript functions, added to `typescript/src/main.ts`, covered by unit tests, and verified with a production build.

| Metric                           | Value                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------- |
| Templates refactored             | 3 (`base.html`, `doctypes.html`, `doctype_detail.html`)                         |
| Templates with no inline JS      | 5 (`connect.html`, `generate_openapi.html`, `faq.html`, `404.html`, `500.html`) |
| TypeScript functions added       | 7                                                                               |
| Global window exposures added    | 4                                                                               |
| Test files created               | 3                                                                               |
| Unit tests written               | 33                                                                              |
| Tests passing                    | 33 / 33                                                                         |
| TypeScript compilation errors    | 0                                                                               |
| Compiled bundle size (`main.js`) | 4.31 kB (gzip: 1.32 kB)                                                         |

---

## Templates Refactored

### 1. `templates/base.html`

**Inline JS removed:**  
An IIFE inside the `<nav>` element that wired up the mobile hamburger-menu toggle button:

```javascript
(function () {
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    const icon = document.getElementById('hamburger-icon');
    if (btn && menu) {
        btn.addEventListener('click', function () { ... });
    }
})();
```

**TypeScript function created — `base(): void`**  
Type annotations applied:

- `btn` → `HTMLButtonElement | null`
- `menu` → `HTMLElement | null`
- `icon` → `HTMLElement | null`

Null-guards replace the bare `if (btn && menu)` check (icon is now guarded too).

**Template change:** The IIFE was removed. `main.js` is loaded as a `type="module"` script alongside the existing `base.js`, `client_error.js` entries in `base.html`.

---

### 2. `templates/doctypes.html`

**Inline JS removed (`{% block extra_js %}`):**  
Full filter/search system for the DocTypes grid, including:

- Deduplication of `<select>` module options using a `Set`
- `filterDocTypes()` — applies search, module, and type filters; toggles the "No Results" banner
- `clearFilters()` — resets all controls
- `?module=` URL query-param deep-link handler

**TypeScript functions created — `doctypes(): void`**  
Type annotations applied:

- `searchInput` → `HTMLInputElement | null`
- `moduleFilter`, `typeFilter` → `HTMLSelectElement | null`
- `clearButton` → `HTMLButtonElement | null`
- `doctypeItems` → `NodeListOf<HTMLElement>` (via `querySelectorAll<HTMLElement>`)
- `noResults` → `HTMLElement | null`
- Dataset properties accessed via `item.dataset.name ?? ""` (avoids implicit `undefined`)
- Local loop variables renamed to `itemName`, `itemModule`, `itemType` to avoid shadowing globals

**Bug fix:** The original code toggled `noResults.classList.toggle('d-none', ...)` which is a Bootstrap class. The template uses Tailwind CSS with `class="hidden"`, so the call was corrected to `classList.toggle('hidden', ...)`.

**Template change:** The entire `{% block extra_js %}` script was replaced with a comment. `main.js` (loaded globally from `base.html`) auto-initialises `doctypes()`.

---

### 3. `templates/doctype_detail.html`

**Inline JS removed (`{% block extra_js %}`):**  
Five separate concerns extracted from one large `<script>` block:

| Original JS function                  | TypeScript function           | Description                                                                          |
| ------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------ |
| `DOMContentLoaded` field-filter setup | `doctype_detail()`            | Wire up field-table search, type, required, and read-only filters                    |
| `openRawDataModal()`                  | `openRawDataModal()`          | Remove `hidden`, add `opacity-100`, trigger Prism highlight                          |
| `closeRawDataModal()`                 | `closeRawDataModal()`         | Add `hidden`, remove `opacity-100`                                                   |
| `copyToClipboard(id)`                 | `copyToClipboard(id: string)` | Clipboard write + popup notification                                                 |
| `initAiPicker(id)`                    | `initAiPicker(id: string)`    | Full AI-provider dropdown: open/close, item selection, clipboard or deep-link action |

Type annotations applied (selected highlights):

- `fieldRows` → `NodeListOf<HTMLTableRowElement>` (via `querySelectorAll<HTMLTableRowElement>`)
- `clearFiltersBtn` renamed from `clearFilters` to avoid shadowing the inner function
- `window.Prism` accessed through a typed intersection: `window as Window & { Prism?: { highlightAll: () => void } }`
- `window.buildDeepLinkingAction` accessed safely with optional chaining via typed intersection
- `this` inside `forEach` item handler typed as `this: HTMLElement`
- All `void navigator.clipboard.writeText(...)` calls prefixed with `void` to silence floating-promise linting

**Global exposures:**  
The four functions that template inline `onclick` handlers depend on are re-attached to `window` using a typed intersection pattern:

```typescript
type ExtendedWindow = Window & {
	openRawDataModal: () => void;
	closeRawDataModal: () => void;
	copyToClipboard: (id: string) => void;
	initAiPicker: (id: string) => void;
};
(window as unknown as ExtendedWindow).openRawDataModal = openRawDataModal;
// ...
```

**Template change:** The entire `{% block extra_js %}` script block was replaced with a Jinja2 comment. The existing `<script type="module" src="...prompt.js">` inside the content block is preserved unchanged.

---

## New Files Created

| File                                      | Purpose                                                                                                               |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `typescript/src/main.ts`                  | TypeScript functions refactored from inline JS                                                                        |
| `typescript/vitest.config.ts`             | Vitest configuration (jsdom environment, coverage via v8)                                                             |
| `typescript/tests/base.test.ts`           | Unit tests for `base()`                                                                                               |
| `typescript/tests/doctypes.test.ts`       | Unit tests for `doctypes()`                                                                                           |
| `typescript/tests/doctype_detail.test.ts` | Unit tests for `doctype_detail()`, `openRawDataModal()`, `closeRawDataModal()`, `copyToClipboard()`, `initAiPicker()` |

---

## Files Modified

| File                            | Change                                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `typescript/src/main.ts`        | Populated from empty → 7 exported TypeScript functions + auto-init                                                                   |
| `typescript/package.json`       | Added `test`, `test:watch`, `test:coverage` scripts; added `vitest`, `@vitest/coverage-v8`, `jsdom`, `@types/jsdom` dev dependencies |
| `typescript/tsconfig.json`      | Extended `include` from `["src"]` to `["src", "tests"]`                                                                              |
| `templates/base.html`           | Removed mobile-menu IIFE; added `main.js` module script                                                                              |
| `templates/doctypes.html`       | Replaced inline filter script with Jinja2 comment                                                                                    |
| `templates/doctype_detail.html` | Replaced inline script block with Jinja2 comment                                                                                     |

---

## Test Results

```
 ✓ tests/base.test.ts            (4 tests)
 ✓ tests/doctypes.test.ts        (8 tests)
 ✓ tests/doctype_detail.test.ts  (21 tests)

 Test Files  3 passed (3)
      Tests  33 passed (33)
   Duration  ~1.3 s
```

---

## Build Output

```
../static/typescript/main.js   4.31 kB │ gzip: 1.32 kB
```

TypeScript compiler (`tsc`) reported zero errors with `strict: true`, `noUnusedLocals: true`, and `noUnusedParameters: true` all enabled.

---

## Challenges & Notes

1. **`noUnusedLocals` strict mode** — The original JS used `module` as a local variable name inside a `forEach` callback. This was renamed to `itemModule` to avoid any ambiguity with TypeScript's module keyword and to satisfy the strict linter.

2. **`void` for floating promises** — `navigator.clipboard.writeText()` returns a `Promise<void>`. In two separate places the original code omitted any error handling. The TypeScript version prefixes these with `void` to make the intentional fire-and-forget explicit.

3. **Bootstrap vs Tailwind class mismatch** — The original `doctypes.html` script toggled the Bootstrap class `d-none` on the `#noResults` element. However, the template uses Tailwind CSS and the element has `class="hidden"`. This was corrected to `hidden` in the TypeScript refactoring.

4. **jsdom `<tr>` parsing** — Unit tests that placed `<tr>` elements inside a raw `<tbody>` fragment (without a wrapping `<table>`) caused jsdom to silently discard the elements. The fix was to wrap the tbody in a `<table>` in the test fixture.

5. **Mobile menu IIFE timing** — The original IIFE ran synchronously inline (after the nav elements existed in the DOM). Since `type="module"` scripts are deferred, the `base()` function runs after full DOM parsing — which is equivalent behaviour.

6. **`main.ts` vs `base.ts`** — The mobile-menu toggle logically belongs in `base.ts` since it shares the base layout context. It was placed in `main.ts` per the SKILL.md convention of mapping each template to a function in `main.ts`. Future maintainers may choose to consolidate into `base.ts`.
