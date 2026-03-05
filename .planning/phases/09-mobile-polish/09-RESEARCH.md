# Phase 9: Mobile Polish - Research

**Researched:** 2026-02-23
**Domain:** Responsive CSS, mobile UX, vanilla JS hamburger menu
**Confidence:** HIGH

## Summary

This phase makes the existing AIAA dashboard fully usable on mobile devices. The codebase is a Flask/Jinja2 app with vanilla CSS (main.css at ~1010 lines, v2.css at ~2000 lines) and vanilla JavaScript. There are no build tools, no CSS preprocessors, and no JS frameworks -- all changes are pure CSS media queries and small JS additions.

The current state has a minimal responsive treatment: `main.css` line 938 hides the sidebar entirely below 768px (`display: none`) and removes the left margin from `.main`. Some templates have their own `@media` rules (dashboard_v2.html at 600px/900px, skill_execute.html at 600px, settings.html at 768px). However, there is NO hamburger menu, no way to access navigation on mobile, and no systematic touch target enforcement.

**Primary recommendation:** Add a hamburger menu overlay system to `base.html` + `main.css`, convert the existing `display: none` sidebar rule to a slide-in overlay, enforce 44x44px touch targets on all interactive elements via a mobile media query block, and ensure form inputs use 16px+ font-size to prevent iOS zoom.

## Standard Stack

No new libraries needed. This phase uses only what already exists in the codebase.

### Core
| Technology | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| CSS Media Queries | CSS3 | Responsive breakpoints | Native, zero-dependency |
| CSS Custom Properties | CSS3 | Theme-consistent mobile styles | Already used throughout |
| Vanilla JavaScript | ES6 | Hamburger toggle, backdrop, Escape key | Matches existing codebase |

### Supporting
| Technology | Purpose | When to Use |
|-----------|---------|-------------|
| `<meta viewport>` | Viewport control | Already present in base.html (line 5) |
| CSS `min-height` / `min-width` | Touch target enforcement | For 44x44px minimum tap areas |
| CSS `transform: translateX()` | Sidebar slide animation | Smooth overlay transition |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|-----------|-----------|----------|
| Vanilla JS hamburger | Bootstrap/Tailwind | Overkill -- adds framework dependency for 20 lines of JS |
| CSS-only hamburger (checkbox hack) | Vanilla JS toggle | JS approach is more accessible (aria-expanded, Escape key) |
| Multiple breakpoints | Single 768px breakpoint | Single breakpoint sufficient for this dashboard's layout |

**Installation:** None required. No new dependencies.

## Architecture Patterns

### Where Changes Go

The mobile polish touches these files:

```
railway_apps/aiaa_dashboard/
├── templates/
│   └── base.html              # Hamburger button + backdrop overlay + JS toggle
├── static/
│   ├── css/
│   │   └── main.css           # Mobile media query block (sidebar, touch targets, forms)
│   └── js/
│       └── main.js            # (optional) Hamburger toggle if not inlined in base.html
```

Plus inline `<style>` blocks in templates that have their own responsive rules:
- `dashboard_v2.html` -- card grids, home-grid, search-hero
- `skill_execute.html` -- form actions, skill header
- `settings.html` -- pref-grid, settings-tabs
- Other templates with existing `@media` rules (clients, help, webhooks, etc.)

### Pattern 1: Hamburger Menu Overlay

**What:** Replace `display: none` with a slide-in overlay sidebar on mobile.

**Current state (main.css line 938-956):**
```css
@media (max-width: 768px) {
    .sidebar {
        display: none;       /* BAD: navigation completely inaccessible */
    }
    .main {
        margin-left: 0;
        padding: 1rem;
    }
}
```

**Target pattern:**
```css
/* Hamburger button -- hidden on desktop, visible on mobile */
.hamburger-btn {
    display: none;           /* hidden on desktop */
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 200;
    width: 44px;
    height: 44px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    color: var(--text-primary);
}

/* Backdrop overlay */
.sidebar-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
}

.sidebar-backdrop.visible {
    display: block;
}

@media (max-width: 768px) {
    .hamburger-btn {
        display: flex;       /* show hamburger on mobile */
    }

    .sidebar {
        transform: translateX(-100%);  /* off-screen by default */
        transition: transform 0.3s ease;
        /* Keep existing fixed positioning, width, z-index */
    }

    .sidebar.open {
        transform: translateX(0);      /* slide in when open */
    }

    .main {
        margin-left: 0;
        padding: 1rem;
        padding-top: 4rem;   /* space for hamburger button */
    }
}
```

**JS toggle (minimal, in base.html):**
```javascript
function toggleMobileNav() {
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.querySelector('.sidebar-backdrop');
    const hamburger = document.querySelector('.hamburger-btn');
    const isOpen = sidebar.classList.contains('open');

    sidebar.classList.toggle('open');
    backdrop.classList.toggle('visible');
    hamburger.setAttribute('aria-expanded', String(!isOpen));

    if (!isOpen) {
        // Focus first nav item when opening
        const firstLink = sidebar.querySelector('.nav-item');
        if (firstLink) firstLink.focus();
    }
}

// Close on backdrop click
document.querySelector('.sidebar-backdrop')
    .addEventListener('click', toggleMobileNav);

// Close on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('open')) {
            toggleMobileNav();
        }
    }
});
```

### Pattern 2: Touch Target Enforcement

**What:** Ensure all interactive elements meet 44x44px minimum tap area.

**Strategy:** Use `min-height: 44px` and padding adjustments inside a `@media (max-width: 768px)` block. Do NOT scale text -- use padding to expand hit area.

```css
@media (max-width: 768px) {
    /* Navigation items */
    .nav-item {
        min-height: 44px;
        padding: 0.75rem 1.25rem;    /* was 0.625rem 1.25rem */
    }

    /* Buttons */
    .btn,
    .btn-secondary,
    .btn-run,
    .btn-estimate {
        min-height: 44px;
    }

    /* Close buttons, icon buttons */
    .modal-close,
    .toast-close,
    .toast__close,
    .qs-star,
    .welcome-banner-close {
        min-width: 44px;
        min-height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Form controls */
    .form-input,
    .form-select,
    .form-textarea,
    .field-input,
    .field-select,
    .field-textarea {
        min-height: 44px;
    }

    /* Category chips/pills */
    .category-chip,
    .category-pill {
        min-height: 44px;
        padding: 0.625rem 1rem;
    }

    /* Logout button */
    .logout-btn {
        min-height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Settings tabs */
    .settings-tab,
    .tab,
    .mode-tab {
        min-height: 44px;
    }

    /* Theme toggle */
    .theme-toggle {
        min-height: 44px;
    }
}
```

### Pattern 3: iOS Zoom Prevention

**What:** Set font-size to 16px on all form inputs on mobile to prevent Safari auto-zoom.

**Critical fact (HIGH confidence):** iOS Safari auto-zooms the viewport when a user focuses any input with `font-size` less than 16px. The current codebase uses `font-size: 0.9375rem` (15px) for `.form-input`, `.form-select`, `.form-textarea`, `.field-input`, `.field-select`, `.field-textarea`, and `font-size: 0.875rem` (14px) for `.cron-select`, `.cron-input`.

```css
@media (max-width: 768px) {
    .form-input,
    .form-select,
    .form-textarea,
    .field-input,
    .field-select,
    .field-textarea,
    .nl-textarea,
    .cron-select,
    .cron-input,
    .cron-input-full,
    .search-bar__input,
    .search-hero-input input {
        font-size: 16px;   /* Prevents iOS zoom on focus */
    }
}
```

### Pattern 4: Card Grid Stacking

**What:** All card grids collapse to single column below 768px.

**Current grids that need treatment:**
1. `.stats-grid` (main.css line 711) -- uses `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))` -- already responsive via auto-fit, but may show 2 columns on phones. Force to 1 column.
2. `.quick-start-grid` (dashboard_v2.html inline) -- uses `repeat(auto-fill, minmax(170px, 1fr))` -- already has 600px breakpoint for 2 columns.
3. `.home-grid` (dashboard_v2.html inline) -- uses `1fr 340px` -- already has 900px breakpoint for 1 column.
4. `.skeleton-grid` -- mirrors quick-start-grid.

```css
@media (max-width: 768px) {
    .stats-grid {
        grid-template-columns: 1fr;
    }

    .quick-start-grid,
    .skeleton-grid {
        grid-template-columns: repeat(2, 1fr);  /* 2 columns on tablet */
    }
}

@media (max-width: 480px) {
    .quick-start-grid,
    .skeleton-grid {
        grid-template-columns: 1fr;    /* 1 column on phones */
    }
}
```

Note: dashboard_v2.html already has `@media (max-width: 600px)` for quick-start-grid at 2 columns. This needs consolidation -- the inline style should be moved to main.css or kept consistent. The 768px breakpoint should force `.home-grid` to single column.

### Anti-Patterns to Avoid

- **Using `display: none` to hide navigation on mobile:** Navigation must remain accessible via hamburger menu. The current `display: none` is the primary problem.
- **Disabling viewport zoom via `maximum-scale=1` or `user-scalable=no`:** This breaks accessibility. Use 16px font-size instead to prevent iOS zoom.
- **Scaling text size to meet touch targets:** Use padding/min-height, not font-size changes, to meet 44x44px requirements.
- **Creating separate mobile templates:** Keep all changes in CSS media queries and minimal JS. No template duplication.
- **Adding a CSS framework for just this phase:** Bootstrap/Tailwind adds massive overhead for what is 100 lines of CSS + 30 lines of JS.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Focus trapping in sidebar overlay | Custom focus management | `trapFocus()` from main.js | Already exists in codebase (main.js line 26-58), battle-tested |
| Viewport meta tag | Custom viewport JS | Existing `<meta name="viewport">` | Already correctly set in base.html line 5 |
| Touch event handling | Custom touch gesture library | CSS `min-height`/`min-width` | Touch target compliance is a CSS sizing problem, not a gesture problem |
| Scroll locking when sidebar open | Complex JS scroll lock | `overflow: hidden` on body | Simple CSS class toggle prevents background scroll |

## Common Pitfalls

### Pitfall 1: iOS Safari Zoom on Input Focus
**What goes wrong:** User taps an input field, Safari zooms the page in and never zooms back out. User must pinch-zoom to navigate.
**Why it happens:** Any `<input>`, `<select>`, or `<textarea>` with font-size below 16px triggers auto-zoom on iOS Safari.
**How to avoid:** Set `font-size: 16px` on ALL form elements within the mobile media query. The codebase currently uses 15px (0.9375rem) and 14px (0.875rem) on form fields.
**Warning signs:** Test by tapping into any input field on an iPhone -- if the page zooms, the font-size is too small.

### Pitfall 2: Sidebar Z-Index Conflicts
**What goes wrong:** Sidebar overlay appears behind modals, toasts, or other overlays.
**Why it happens:** The sidebar is `z-index: 100` (main.css line 72). Modal overlay is `z-index: 1000`. Confirm modal is `z-index: 10000`. Toast is `z-index: 9999`.
**How to avoid:** Keep sidebar at z-index 100, backdrop at z-index 99. These are below all other overlays, which is correct -- modals should appear above the sidebar.
**Warning signs:** Open the sidebar on mobile, then trigger a modal. Modal should appear above sidebar.

### Pitfall 3: Conflicting Media Query Breakpoints
**What goes wrong:** Styles fight each other because inline `<style>` blocks in templates use different breakpoints (600px, 768px, 900px) than main.css (768px).
**Why it happens:** Each template was developed independently with its own responsive rules.
**How to avoid:** Do NOT change existing template-specific breakpoints. Add the new mobile rules to `main.css` at the 768px breakpoint. The template-specific rules at 600px provide additional refinement for smaller screens, which is fine.
**Warning signs:** Test at exactly 768px, 600px, and 480px -- watch for visual jumps or conflicting layouts.

### Pitfall 4: Hamburger Button Overlapping Content
**What goes wrong:** The fixed hamburger button covers page content, especially page titles.
**Why it happens:** Fixed positioning takes the button out of flow.
**How to avoid:** Add `padding-top` to `.main` in the mobile media query to push content below the hamburger button area. The current `padding: 1rem` is not enough -- use `padding-top: 4rem` to create space.
**Warning signs:** First element on any page is hidden behind the hamburger button.

### Pitfall 5: Sidebar Close on Navigation
**What goes wrong:** User taps a nav link, sidebar stays open over the new page.
**Why it happens:** Standard page navigation triggers a full page load, so the sidebar state resets. This is actually NOT a problem for this server-rendered app.
**How to avoid:** No action needed -- each page load resets to sidebar closed. If this were an SPA, you would need to close sidebar on route change.

### Pitfall 6: Body Scroll Lock Missing
**What goes wrong:** User can scroll the main content behind the open sidebar overlay.
**Why it happens:** The backdrop covers the viewport visually but `body` is still scrollable.
**How to avoid:** Add `overflow: hidden` to `body` when sidebar is open. Remove when closed.
```javascript
document.body.style.overflow = isOpen ? '' : 'hidden';
```

## Code Examples

### Complete Hamburger Button HTML (for base.html)
```html
<!-- Add before <aside class="sidebar"> -->
<button class="hamburger-btn" onclick="toggleMobileNav()" aria-label="Open navigation menu" aria-expanded="false">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="12" x2="21" y2="12"/>
        <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
</button>

<!-- Add after </aside> and before <main> -->
<div class="sidebar-backdrop" onclick="toggleMobileNav()"></div>
```

### Complete Mobile CSS Block (for main.css)
```css
/* ===== Mobile Responsive ===== */

/* Hamburger button (hidden on desktop) */
.hamburger-btn {
    display: none;
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 200;
    width: 44px;
    height: 44px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    color: var(--text-primary);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.sidebar-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
}

.sidebar-backdrop.visible {
    display: block;
}

@media (max-width: 768px) {
    /* Hamburger visible */
    .hamburger-btn {
        display: flex;
    }

    /* Sidebar: slide-in overlay */
    .sidebar {
        transform: translateX(-100%);
        transition: transform 0.3s ease;
    }

    .sidebar.open {
        transform: translateX(0);
    }

    /* Main content */
    .main {
        margin-left: 0;
        padding: 1rem;
        padding-top: 4rem;
    }

    /* Page header adjustments */
    .page-title {
        font-size: 1.25rem;
    }

    /* Stats grid to single column */
    .stats-grid {
        grid-template-columns: 1fr;
    }

    /* Modal full-width */
    .modal {
        width: 95%;
        max-height: 95vh;
    }

    /* Touch targets: 44px minimum */
    .nav-item {
        min-height: 44px;
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
    }

    .btn,
    .btn-secondary,
    .btn-run,
    .btn-estimate,
    .mode-tab,
    .settings-tab,
    .tab,
    .theme-toggle,
    .logout-btn,
    .category-chip,
    .category-pill {
        min-height: 44px;
    }

    .modal-close,
    .toast-close,
    .toast__close,
    .qs-star,
    .welcome-banner-close,
    .search-bar__clear {
        min-width: 44px;
        min-height: 44px;
    }

    .form-input,
    .form-select,
    .form-textarea,
    .field-input,
    .field-select,
    .field-textarea,
    .nl-textarea,
    .cron-select,
    .cron-input,
    .cron-input-full,
    .search-bar__input,
    .search-hero-input input {
        font-size: 16px;
        min-height: 44px;
    }

    /* Toast positioning */
    .toast-notification {
        left: 1rem;
        right: 1rem;
        bottom: 1rem;
        min-width: auto;
    }

    .toast-container {
        left: 1rem;
        right: 1rem;
        bottom: 1rem;
        max-width: none;
    }

    /* Form buttons stack vertically */
    .form-actions {
        flex-direction: column;
    }

    .form-actions .btn-run,
    .form-actions .btn-estimate {
        width: 100%;
        justify-content: center;
    }

    /* Data tables scroll horizontally */
    .data-table {
        display: block;
        overflow-x: auto;
    }
}
```

### Complete Toggle JS (for base.html)
```javascript
function toggleMobileNav() {
    var sidebar = document.querySelector('.sidebar');
    var backdrop = document.querySelector('.sidebar-backdrop');
    var btn = document.querySelector('.hamburger-btn');
    var isOpen = sidebar.classList.contains('open');

    sidebar.classList.toggle('open');
    backdrop.classList.toggle('visible');
    btn.setAttribute('aria-expanded', String(!isOpen));
    document.body.style.overflow = isOpen ? '' : 'hidden';

    if (!isOpen) {
        var firstLink = sidebar.querySelector('.nav-item');
        if (firstLink) firstLink.focus();
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('open')) {
            toggleMobileNav();
            document.querySelector('.hamburger-btn').focus();
        }
    }
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|-------------|-----------------|-------------|--------|
| `display: none` sidebar on mobile | Hamburger + slide-in overlay | Standard since ~2015 | Users can actually navigate on mobile |
| `user-scalable=no` for zoom prevention | `font-size: 16px` on inputs | Accessibility standards tightened ~2020 | Preserves user zoom ability |
| Fixed px breakpoints per element | Single 768px breakpoint + auto-fit grids | CSS Grid adoption ~2018 | Less CSS, more consistent behavior |
| Separate mobile CSS file | Single file with media query blocks | Modern best practice | Easier maintenance, no flash of wrong styles |

**Already correct in codebase:**
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">` -- present and correct in base.html
- v2.css uses mobile-first `min-width` breakpoints for some components (quick-start-grid, role-card-grid)
- Several templates already have `@media (max-width: 600px)` for form stacking

**Current issues:**
- Sidebar is `display: none` on mobile with no alternative navigation (main.css line 939)
- Form inputs use 15px font-size (0.9375rem), causing iOS zoom
- No touch target enforcement
- `.home-grid` uses fixed `1fr 340px` that only breaks at 900px (inline in dashboard_v2.html)

## Existing Responsive Rules Inventory

These already exist and should NOT be duplicated:

| File | Breakpoint | What It Does |
|------|-----------|-------------|
| main.css:938 | max-width: 768px | Hides sidebar, removes margin (to be REPLACED) |
| dashboard_v2.html:423 | max-width: 600px | Welcome banner steps stack vertically |
| dashboard_v2.html:430 | max-width: 900px | Home-grid goes single column |
| dashboard_v2.html:436 | max-width: 600px | Search hero stacks, quick-start 2 columns |
| skill_execute.html:571 | max-width: 600px | Skill header stacks, form actions stack |
| settings.html:307 | max-width: 768px | Pref-grid single column |
| clients.html:246 | max-width: 768px | Client toolbar stacks |
| help.html:267 | max-width: 768px | Help sections single column |
| webhooks.html:181 | max-width: 768px | Action bar stacks |
| execution_history.html:221 | max-width: 768px | Timeline adjustments |
| workflow_catalog.html:105 | max-width: 768px | Workflows grid single column |
| workflow_detail.html:203 | max-width: 768px | Workflow title row stacks |
| deploy_wizard.html:403 | max-width: 768px | Deploy type grid single column |
| error_v2.html:135 | max-width: 768px | Error actions stack |
| v2.css:1993 | max-width: 768px | Skeleton workflows grid single column |
| v2.css:1999 | max-width: 600px | Skeleton grid 2 columns |
| login.html:201 | max-width: 480px | Login card padding reduced |
| onboarding.html:478 | max-width: 560px | Onboarding card adjustments |

## Open Questions

1. **Template inline styles vs main.css consolidation**
   - What we know: Many templates have their own `<style>` blocks with responsive rules
   - What's unclear: Should we move ALL responsive rules to main.css for maintainability, or leave template-specific rules inline?
   - Recommendation: Leave existing template-specific rules in place. Add ONLY the new mobile rules (hamburger, touch targets, iOS zoom) to main.css. Avoid churn.

2. **Login page sidebar**
   - What we know: login.html does NOT extend base.html -- it's a standalone page with its own styles
   - What's unclear: Does it need any mobile treatment?
   - Recommendation: Login page is already centered/responsive with max-width: 420px. No changes needed.

3. **Onboarding page sidebar**
   - What we know: onboarding.html also has standalone styling (does not use sidebar)
   - Recommendation: No hamburger menu needed on onboarding. Already responsive.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `base.html`, `main.css`, `v2.css`, `dashboard_v2.html`, `skill_execute.html`, `settings.html` -- direct file reads
- [16px or Larger Text Prevents iOS Form Zoom (CSS-Tricks)](https://css-tricks.com/16px-or-larger-text-prevents-ios-form-zoom/) -- iOS zoom prevention
- [WCAG 2.5.8 Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) -- 44x44px touch target standard (from Phase 8 accessibility work)

### Secondary (MEDIUM confidence)
- [Accessible Hamburger Menu + Slide Out Navigation (Impressive Webs)](https://www.impressivewebs.com/accessible-keyboard-friendly-hamburger-menu-slide-out-navigation/) -- accessible hamburger pattern with aria-expanded, Escape key, focus management
- [W3Schools Mobile Navigation Menu](https://www.w3schools.com/howto/howto_js_mobile_navbar.asp) -- basic pattern reference

### Tertiary (LOW confidence)
- None. All findings verified against codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure CSS/JS, verified against existing codebase
- Architecture: HIGH -- patterns directly derived from reading all affected files
- Pitfalls: HIGH -- iOS zoom issue verified (current font-sizes are 0.9375rem = 15px), z-index hierarchy verified from codebase, existing breakpoint inventory compiled from all templates

**Research date:** 2026-02-23
**Valid until:** No expiration -- this is CSS/HTML fundamentals with codebase-specific findings
