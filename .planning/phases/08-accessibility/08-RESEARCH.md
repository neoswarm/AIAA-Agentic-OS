# Phase 8: Accessibility - Research

**Researched:** 2026-02-23
**Domain:** WCAG AA compliance, ARIA, keyboard navigation, focus management (vanilla JS + CSS)
**Confidence:** HIGH

## Summary

This research audits the current accessibility state of the AIAA Dashboard (Flask + Jinja2 + vanilla JS + CSS custom properties) across all templates, stylesheets, and JavaScript files. The dashboard has significant accessibility gaps: zero ARIA roles on interactive regions, zero `aria-live` regions for dynamic content, zero skip-to-content links, zero focus trapping in modals, pervasive `outline: none` without visible focus replacements on non-input elements, multiple WCAG AA color contrast failures, and several non-semantic interactive `<div>` elements with `onclick` handlers.

The good news: the codebase is relatively small (~22 templates, 2 CSS files, 9 JS files), uses semantic HTML in many places (proper `<nav>`, `<main>`, `<aside>`, `<form>`, `<label for="">` on most forms), and has a centralized utility layer (`main.js`) that makes adding global accessibility patterns straightforward. The theme toggle, toast notifications, and confirmation modal are all centralized, so fixing them fixes the entire app.

**Primary recommendation:** Fix this in two passes -- (1) ARIA + focus management audit/fixes across all templates and JS, then (2) color contrast fixes + keyboard navigation for all interactive patterns.

## Standard Stack

No external libraries needed. This is a pure CSS + vanilla JS accessibility implementation.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Native ARIA attributes | HTML5 | Semantic accessibility | Built into HTML spec, zero dependencies |
| CSS `:focus-visible` | CSS4 | Visible focus indicators | Native browser support, no JS needed |
| `<dialog>` element | HTML5.2 | Accessible modals | Built-in focus trap, Escape handling, backdrop |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `aria-live="polite"` | Announce dynamic content | Toast notifications, search results, form validation |
| `role="dialog"` + `aria-modal="true"` | Modal accessibility | All modal overlays (confirm, client form, webhook, deploy wizard) |
| `tabindex="-1"` | Programmatic focus targets | Skip links, modal headings, error summaries |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom focus trap JS | `<dialog>` element | `<dialog>` has native trap + Escape; use for new modals, custom JS for existing overlays |
| aria-live on toasts | Third-party toast library | Unnecessary -- just add `aria-live` to existing toast container |

## Architecture Patterns

### Pattern 1: Focus Trap for Modals (vanilla JS)

**What:** Trap keyboard focus inside modal overlays so Tab/Shift+Tab cycle within the modal.
**When to use:** Every modal overlay (confirm modal, client form, webhook form, deploy wizard, API key modals).
**Source:** W3C APG Dialog Modal Pattern (https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)

```javascript
/**
 * Trap focus within a modal element.
 * Call on modal open; returns a cleanup function to call on close.
 */
function trapFocus(modalElement) {
    const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusableElements = modalElement.querySelectorAll(focusableSelectors);
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    function handleKeydown(e) {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }
        if (e.key === 'Escape') {
            // Close modal -- caller provides close logic
            modalElement.dispatchEvent(new CustomEvent('modal-escape'));
        }
    }

    modalElement.addEventListener('keydown', handleKeydown);

    // Focus first focusable element
    if (firstFocusable) firstFocusable.focus();

    return function cleanup() {
        modalElement.removeEventListener('keydown', handleKeydown);
    };
}
```

### Pattern 2: Accessible Toast Notifications

**What:** Make toast container an `aria-live` region so screen readers announce them.
**When to use:** The global toast container in `base.html`.

```html
<!-- In base.html, modify existing toast container -->
<div id="toast-container" class="toast-container" aria-live="polite" aria-atomic="true"></div>
```

```javascript
// In showToast(), set role="alert" for errors, role="status" for info/success
toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
```

### Pattern 3: Skip-to-Content Link

**What:** Hidden link that becomes visible on focus, jumps past sidebar navigation.
**When to use:** `base.html`, before the sidebar.

```html
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <aside class="sidebar">...</aside>
    <main class="main" id="main-content" tabindex="-1">
        {% block content %}{% endblock %}
    </main>
</body>
```

```css
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--accent);
    color: white;
    padding: 0.5rem 1rem;
    z-index: 10000;
    font-size: 0.875rem;
    font-weight: 500;
    border-radius: 0 0 8px 0;
    transition: top 0.2s;
}

.skip-link:focus {
    top: 0;
}
```

### Pattern 4: Visible Focus Indicators

**What:** Replace `outline: none` with visible `:focus-visible` styles that only show on keyboard navigation.
**When to use:** Global CSS reset, all interactive elements.

```css
/* Global focus-visible style -- add to main.css */
:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

/* Remove the problematic outline:none from inputs and replace with focus-visible */
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
    outline: none; /* Keep for mouse focus */
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-muted);
}

.form-input:focus-visible,
.form-select:focus-visible,
.form-textarea:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -1px;
}
```

### Pattern 5: Accessible Search Combobox

**What:** The search dropdown in dashboard_v2 functions as a combobox and needs proper ARIA.
**When to use:** Home page search, skill catalog search.

```html
<div class="search-hero-input" role="combobox" aria-expanded="false" aria-haspopup="listbox" aria-owns="search-results">
    <input type="text"
           id="skill-search"
           role="searchbox"
           aria-autocomplete="list"
           aria-controls="search-results"
           aria-label="Search skills"
           placeholder="What do you want to do?..."
           autocomplete="off">
    <div id="search-results" role="listbox" aria-label="Search results">
        <!-- Results get role="option" -->
    </div>
</div>
```

### Anti-Patterns to Avoid
- **`<div onclick="...">` for interactive elements:** These are not keyboard accessible. Use `<button>` instead, or add `role="button"`, `tabindex="0"`, and keydown handler for Enter/Space.
- **`outline: none` without replacement:** Removes the only focus indicator for keyboard users. Always pair with `:focus-visible` alternative.
- **Toasts without `aria-live`:** Screen readers never announce them. Dynamic content needs live regions.
- **Modals without focus trap:** Keyboard users tab into background content and get lost.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Focus indicators | Custom JS focus tracking | CSS `:focus-visible` pseudo-class | Natively distinguishes keyboard vs mouse focus |
| Modal focus trapping | Complex event delegation | `trapFocus()` utility (see pattern above) | Simple, testable, reusable function |
| Screen reader announcements | Custom JS polling | `aria-live` regions | Native browser/SR integration |
| Accessible tooltips | Custom hover-only tooltips | `title` attr + `aria-describedby` on hover tooltips | CSS-only `:hover` tooltips are invisible to keyboard/SR users |
| Contrast checking | Manual eyeball testing | Computed ratios (see contrast data below) | Math, not opinion |

## Common Pitfalls

### Pitfall 1: outline: none Without Focus-Visible Replacement
**What goes wrong:** Keyboard users cannot see which element has focus.
**Why it happens:** Developers remove outlines for aesthetics without adding alternative indicators.
**How to avoid:** Use `:focus-visible` to show focus ring only on keyboard navigation.
**Warning signs:** Any CSS rule with `outline: none` or `outline: 0`.

**Current codebase impact:** Found 19 instances of `outline: none` across templates and CSS files:
- `main.css` (3 instances): `.form-input:focus`, `.form-select:focus`, `.form-textarea:focus`
- `v2.css` (1 instance): `.search-bar__input:focus`
- Templates with inline styles (15 instances): login.html, skill_execute.html, onboarding.html, help.html, events.html, webhooks.html, workflow_catalog.html, env.html, setup.html, dashboard_v2.html, execution_history.html

### Pitfall 2: Non-Semantic Interactive Elements
**What goes wrong:** `<div onclick="...">` elements are invisible to screen readers and unreachable via keyboard Tab.
**Why it happens:** Quick implementation uses divs instead of buttons.
**How to avoid:** Use `<button>` or add `role="button"` + `tabindex="0"` + keydown handler.
**Warning signs:** Any `<div>` or `<span>` with an `onclick` attribute.

**Current codebase impact:** Found 9 instances of `<div onclick>`:
- `base.html`: theme-toggle div (line 25), nav-label-advanced div (line 82)
- `onboarding.html`: 4 role-cards (lines 523-544), 3 task-cards (lines 602-614)

### Pitfall 3: Missing ARIA on Dynamic Content
**What goes wrong:** Screen readers don't announce dynamically loaded/changed content.
**Why it happens:** Content is updated via `innerHTML` without live region markup.
**How to avoid:** Wrap dynamic content areas in `aria-live` regions.
**Current codebase impact:**
- Toast notifications: No `aria-live` on `#toast-container`
- Search results dropdown: No `role="listbox"` or live region
- Skeleton-to-content transitions: No announcement when data loads
- Form validation messages: No `aria-live` or `role="alert"`

### Pitfall 4: Modals Without Focus Management
**What goes wrong:** When modal opens, focus stays behind it. Keyboard users tab through background.
**Why it happens:** Modal show/hide only toggles CSS visibility.
**How to avoid:** On open: trap focus, set aria-modal. On close: return focus to trigger.
**Current codebase impact:** All 5+ modal patterns lack focus management:
- `confirmAction()` in main.js (line 142)
- Client form overlay in clients.html
- Webhook add modal in webhooks.js
- API key modals in api_keys.html
- Deploy wizard in deploy_wizard.html

### Pitfall 5: Labels Without `for` Attribute
**What goes wrong:** Clicking label doesn't focus input. Screen readers can't associate label with field.
**Why it happens:** Labels use class-based styling without explicit `for` attribute.
**How to avoid:** Every `<label>` needs `for="input-id"` matching the input's `id`.
**Current codebase impact:** Several labels missing `for`:
- `api_keys.html`: "Key Name" label, "Permissions" label, "Expiration" label
- `env.html`: "Variable Name" label, "Value" label
- `deploy_wizard.html`: Multiple form labels
- `events.html`: Filter labels
- `clients.html`: "Brand Voice" label (line 382)
- `skill_execute.html`: Client label (uses wrapping, acceptable but has no `id` on associated elements)
- Dynamically generated form fields (skill_execution.js) -- need audit

### Pitfall 6: SVG Icons Without Accessible Names
**What goes wrong:** Screen readers announce meaningless SVG paths or skip icons entirely.
**Why it happens:** Decorative SVGs and meaningful SVGs treated the same.
**How to avoid:** Decorative SVGs get `aria-hidden="true"`. Meaningful SVGs (icon-only buttons) need `aria-label` on the button.
**Current codebase impact:** All sidebar nav SVGs, all icon buttons, and all card icons lack `aria-hidden="true"`. Most are decorative (paired with text labels), but icon-only buttons (settings icon-btn, help icon-btn in dashboard_v2) need labels.

## Color Contrast Audit

### Computed WCAG AA Contrast Ratios

WCAG AA thresholds: 4.5:1 for normal text (< 18pt / 14pt bold), 3:1 for large text and UI components.

#### FAILURES -- Must Fix

| Combination | Context | Ratio | AA Normal | AA Large | Fix |
|-------------|---------|-------|-----------|----------|-----|
| White (#fff) on accent (#e07a3a) | Dark: all `.btn` buttons | 2.99:1 | FAIL | FAIL | Darken accent or use dark text on buttons |
| White (#fff) on accent (#d96c2c) | Light: all `.btn` buttons | 3.42:1 | FAIL | PASS | Use dark text or darken background |
| Warning (#ca8a04) on white (#fff) | Light: warning badges/text | 2.94:1 | FAIL | FAIL | Darken warning to ~#92600a |

#### BORDERLINE -- Fix for Normal Text

| Combination | Context | Ratio | AA Normal | AA Large |
|-------------|---------|-------|-----------|----------|
| text-muted (#737373) on bg-base (#1a1a1a) | Dark: muted labels | 3.67:1 | FAIL | PASS |
| text-muted (#737373) on bg-surface (#232323) | Dark: muted text on cards | 3.31:1 | FAIL | PASS |
| text-muted (#737373) on bg-elevated (#2a2a2a) | Dark: muted text on elevated | 3.03:1 | FAIL | PASS |
| text-muted (#737373) on bg-base (#f8f8f8) | Light: muted labels | 4.46:1 | FAIL (barely) | PASS |
| text-muted (#737373) on bg-elevated (#f0f0f0) | Light: muted on elevated | 4.16:1 | FAIL | PASS |
| accent (#d96c2c) on all light bgs | Light: links, active nav | 3.01-3.42:1 | FAIL | PASS |
| Login primary (#6366f1) on bg-elevated (#141414) | Login page dark | 4.12:1 | FAIL | PASS |
| Login text-muted (#737373) on bg-base (#0a0a0a) | Login page dark | 4.18:1 | FAIL | PASS |

#### PASSING (no action needed)

| Combination | Context | Ratio |
|-------------|---------|-------|
| text-primary on all backgrounds (both themes) | All primary text | 13.17-17.40:1 |
| text-secondary on all backgrounds (both themes) | Body text | 5.69-7.81:1 |
| success (#4ade80) on dark surfaces | Success badges | 9.02:1 |
| error (#f87171) on dark surfaces | Error badges | 5.68:1 |
| error (#dc2626) on light surfaces | Error badges | 4.83:1 |
| success (#16a34a) on light surfaces | Success badges | 3.30:1 (large only) |

### Recommended Color Fixes

```css
/* Dark theme fixes */
:root {
    --text-muted: #8a8a8a;        /* Was #737373, now 4.58:1 on #1a1a1a */
    /* --accent stays #e07a3a but button text changes */
}

/* Light theme fixes */
[data-theme="light"] {
    --text-muted: #666666;        /* Was #737373, now 5.74:1 on #ffffff */
    --accent: #b85a1e;            /* Was #d96c2c, now ~4.5:1 on #ffffff */
    --warning: #92600a;           /* Was #ca8a04, now ~4.5:1 on #ffffff */
}

/* Button text -- use dark text on accent background in both themes */
.btn {
    color: #1a1a1a;  /* Dark text instead of white for 4.5:1+ */
    /* OR darken accent so white passes */
}
```

**Recommended approach for buttons:** Darken the dark-theme accent to ~#c06520 (white gets ~4.5:1) and the light-theme accent to ~#a04d15 (white gets ~6.5:1). This preserves the orange brand identity while meeting contrast.

## Current State Audit by Template

### base.html (affects ALL pages)
- **Missing:** Skip-to-content link
- **Missing:** `role="navigation"` on `<nav>` (already semantic, but needs `aria-label`)
- **Missing:** `role="complementary"` or `aria-label` on `<aside>`
- **Missing:** `aria-live` on `#toast-container`
- **Missing:** `aria-hidden="true"` on all decorative SVGs in nav
- **Fix needed:** Theme toggle is a `<div onclick>` -- must be `<button>`
- **Fix needed:** Advanced nav toggle is a `<div onclick>` -- must be `<button>`
- **Fix needed:** Theme toggle needs `aria-label="Toggle dark/light theme"`
- **Missing:** `id="main-content"` on `<main>` for skip link target

### login.html
- **Good:** Labels have `for` attributes, inputs have `id`s, form is semantic
- **Fix needed:** Login page uses own CSS variables (different from main.css) -- needs same contrast fixes
- **Fix needed:** Theme toggle button needs `aria-label`
- **Fix needed:** Error message div needs `role="alert"`

### dashboard_v2.html
- **Partial:** Favorite star buttons have `aria-label` (good!)
- **Missing:** Search input needs `aria-label` (no visible label)
- **Missing:** Search results dropdown needs `role="listbox"`, items need `role="option"`
- **Missing:** Icon-only buttons (settings, help) have `title` but no `aria-label`
- **Missing:** Category chips container needs `role="tablist"` or similar, chips need roles
- **Missing:** Skeleton loaders need `aria-hidden="true"` and live region for loaded state

### skill_execute.html
- **Fix needed:** Mode tabs need `role="tablist"`, tabs need `role="tab"`, panels need `role="tabpanel"`
- **Fix needed:** Dynamic form fields (generated by JS) need proper `id` + `for` association
- **Missing:** Field error messages need `aria-live="polite"` or `role="alert"`
- **Missing:** Tooltip (CSS `:hover::after`) is invisible to keyboard/screen readers

### onboarding.html
- **Fix needed:** 4 role-cards and 3 task-cards are `<div onclick>` -- need `role="button"` + `tabindex="0"` + keydown, or use `<button>`
- **Fix needed:** Progress dots need `aria-label` or role description
- **Good:** API key input has proper `<label for>`

### settings.html
- **Good:** Most labels have proper `for` attributes
- **Good:** Toggle switches use `<label>` wrapping with `:focus-visible` style
- **Fix needed:** Tabs need `role="tablist"` / `role="tab"` / `role="tabpanel"`

### clients.html
- **Good:** Most labels have `for` attributes
- **Fix needed:** Client form modal needs focus trap + `role="dialog"` + `aria-modal="true"`
- **Fix needed:** Brand Voice label (line 382) missing `for` attribute
- **Fix needed:** Close overlay on Escape key

### help.html
- **Fix needed:** FAQ accordions (`<button class="faq-question">`) need `aria-expanded` attribute
- **Fix needed:** FAQ answers need `role="region"` or `aria-hidden` toggle
- **Fix needed:** Search input needs `aria-label`

### webhooks.html, api_keys.html, deploy_wizard.html
- **Fix needed:** All modals need `role="dialog"`, `aria-modal="true"`, focus trap, Escape handling
- **Fix needed:** Labels missing `for` attributes on several form fields

### execution_history.html
- **Fix needed:** Expandable rows (`onclick="toggleExecutionDetails"`) need `aria-expanded`
- **Fix needed:** Retry/View Logs buttons within rows need clear labels

### error_v2.html
- **Mostly OK:** Simple page with retry button
- **Fix needed:** Error icon SVG needs `aria-hidden="true"`, error text is already readable

## Code Examples

### Example 1: Accessible Confirmation Modal (update main.js)

```javascript
// Source: W3C APG Dialog Modal Pattern
function confirmAction(message) {
    return new Promise((resolve) => {
        const existingModal = document.querySelector('.confirm-modal-overlay');
        if (existingModal) existingModal.remove();

        // Store the element that triggered the modal
        const triggerElement = document.activeElement;

        const modal = document.createElement('div');
        modal.className = 'confirm-modal-overlay';
        modal.innerHTML = `
            <div class="modal confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message">
                <div class="modal-header">
                    <span class="modal-title" id="confirm-title">Confirm Action</span>
                </div>
                <div class="modal-body">
                    <p id="confirm-message">${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary btn" id="confirm-cancel">Cancel</button>
                    <button class="btn" id="confirm-ok">Confirm</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Focus trap
        const cleanup = trapFocus(modal.querySelector('.confirm-modal'));

        function close(result) {
            cleanup();
            modal.remove();
            // Return focus to trigger element
            if (triggerElement && triggerElement.focus) triggerElement.focus();
            resolve(result);
        }

        modal.querySelector('#confirm-cancel').addEventListener('click', () => close(false));
        modal.querySelector('#confirm-ok').addEventListener('click', () => close(true));
        modal.addEventListener('click', (e) => {
            if (e.target === modal) close(false);
        });
        modal.querySelector('.confirm-modal').addEventListener('modal-escape', () => close(false));
    });
}
```

### Example 2: Making div-based Toggle Accessible

```html
<!-- Before (inaccessible) -->
<div class="theme-toggle" onclick="toggleTheme()">
    <svg>...</svg>
    <span>Toggle Theme</span>
</div>

<!-- After (accessible) -->
<button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark and light theme">
    <svg aria-hidden="true">...</svg>
    <span>Toggle Theme</span>
</button>
```

### Example 3: Accessible FAQ Accordion

```html
<div class="faq-item">
    <button class="faq-question"
            aria-expanded="false"
            aria-controls="faq-answer-1"
            onclick="toggleFaq(this)">
        How do I add an API key?
        <svg aria-hidden="true">...</svg>
    </button>
    <div class="faq-answer" id="faq-answer-1" role="region" hidden>
        <p>Go to Settings and enter your key...</p>
    </div>
</div>
```

```javascript
function toggleFaq(button) {
    const expanded = button.getAttribute('aria-expanded') === 'true';
    const answerId = button.getAttribute('aria-controls');
    const answer = document.getElementById(answerId);

    button.setAttribute('aria-expanded', String(!expanded));
    if (expanded) {
        answer.hidden = true;
    } else {
        answer.hidden = false;
    }
}
```

### Example 4: Accessible Tab Pattern (for mode-tabs, settings-tabs)

```html
<div class="mode-tabs" role="tablist" aria-label="Skill input mode">
    <button class="mode-tab active" role="tab" aria-selected="true"
            aria-controls="form-mode-container" id="tab-form"
            onclick="switchMode('form')">Form</button>
    <button class="mode-tab" role="tab" aria-selected="false"
            aria-controls="nl-mode-container" id="tab-nl"
            onclick="switchMode('nl')">Natural Language</button>
</div>

<div class="skill-form-card" id="form-mode-container" role="tabpanel" aria-labelledby="tab-form">
    ...
</div>
<div class="nl-mode-container" id="nl-mode-container" role="tabpanel" aria-labelledby="tab-nl" hidden>
    ...
</div>
```

```javascript
function switchMode(mode) {
    document.querySelectorAll('[role="tab"]').forEach(tab => {
        tab.setAttribute('aria-selected', 'false');
        tab.classList.remove('active');
    });
    document.querySelectorAll('[role="tabpanel"]').forEach(panel => {
        panel.hidden = true;
    });

    const activeTab = document.getElementById('tab-' + mode);
    const activePanel = document.getElementById(mode + '-mode-container');
    activeTab.setAttribute('aria-selected', 'true');
    activeTab.classList.add('active');
    activePanel.hidden = false;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `:focus` for all focus styling | `:focus-visible` for keyboard-only | CSS4 / 2022+ | Mouse users don't see focus rings, keyboard users do |
| Custom modal `<div>` focus trap | `<dialog>` with `showModal()` | HTML 5.2 / 2022+ | Built-in focus trap, Escape key, backdrop, inert background |
| `outline: none` everywhere | Never remove outline without replacement | WCAG 2.1 / 2018 | Keyboard users need visible focus |
| ARIA everywhere | Prefer semantic HTML, ARIA as supplement | Always | `<button>` > `<div role="button">`, `<nav>` > `<div role="navigation">` |

**Note on `<dialog>`:** While `<dialog>` is the modern standard, the existing codebase uses `<div class="modal-overlay">` patterns extensively. Migrating all modals to `<dialog>` would require significant HTML restructuring. **Recommended approach:** Add `trapFocus()` utility to `main.js` and use it with existing modal patterns, rather than rewriting all modals as `<dialog>`. This is faster and achieves the same accessibility outcome.

## Open Questions

1. **Dynamic form field accessibility**
   - What we know: `skill_execution.js` generates form fields dynamically via `innerHTML`
   - What's unclear: Whether generated labels correctly associate with generated inputs (need to check the `loadSkillForm` rendering code more closely during implementation)
   - Recommendation: Audit during Plan 08-01 implementation; ensure all generated fields have `id` + matching `<label for>`

2. **Mobile sidebar behavior**
   - What we know: Sidebar is fixed-position with `width: 240px`
   - What's unclear: Whether mobile has a hamburger menu or the sidebar is always visible
   - Recommendation: If no mobile menu exists, this is Phase 1 territory, not Phase 8

3. **Tooltip accessibility on skill form fields**
   - What we know: Tooltips use CSS `::after` pseudo-element on `:hover`
   - What's unclear: Whether to make these focusable (adds tabstops) or use a different pattern
   - Recommendation: Add `tabindex="0"` to tooltip triggers and show on `:focus` as well as `:hover`; add `aria-describedby` linking to a visually-hidden span with the tooltip text

## Sources

### Primary (HIGH confidence)
- W3C WAI-ARIA Authoring Practices Guide - Dialog Modal Pattern: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- MDN aria-modal attribute: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-modal
- WebAIM Contrast Checker methodology: https://webaim.org/resources/contrastchecker/
- Direct codebase audit of all 22 templates, 2 CSS files, 9 JS files (performed 2026-02-23)

### Secondary (MEDIUM confidence)
- Hidde de Vries - Using JavaScript to trap focus: https://hidde.blog/using-javascript-to-trap-focus-in-an-element/
- UXPin - How to Build Accessible Modals with Focus Traps: https://www.uxpin.com/studio/blog/how-to-build-accessible-modals-with-focus-traps/
- TheWCAG - Accessible Modals & Dialogs 2026 guide: https://www.thewcag.com/examples/modals-dialogs

### Computed Data (HIGH confidence)
- All contrast ratios computed using WCAG 2.0 relative luminance formula against actual CSS custom property values extracted from `main.css` lines 1-43

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no external libs needed, pure HTML/CSS/JS patterns
- Architecture: HIGH - patterns from W3C APG, verified against codebase structure
- Pitfalls: HIGH - all findings from direct codebase audit with line numbers
- Color contrast: HIGH - mathematically computed from actual CSS values

**Research date:** 2026-02-23
**Valid until:** 2026-06-23 (WCAG spec is stable, codebase may change with other phases)
