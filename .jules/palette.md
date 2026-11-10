# Palette UX & Accessibility Journal

## 2025-05-18 - Scotopic-Safe Focus Ring Adaptive Pattern
**Learning:** In astronomical imaging software operating under nocturnal field conditions, default high-contrast focus rings (like bright blue or cyan) can destroy dark adaptation (scotopic vision). Adapting focus ring outlines to match active night vision themes (e.g. `focus-visible:ring-red-500` in OLED Crimson mode vs `focus-visible:ring-emerald-400` in standard dark mode) ensures full keyboard accessibility (WCAG 2.4.7 Focus Visible) without compromising visual acuity for telescope operators.
**Action:** Always provide theme-aware focus ring classes (`focusRing` helper with `focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-black`) and pair all icon-only control buttons with explicit `aria-label` and `aria-pressed` states.
