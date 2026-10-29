# Palette's UX Journal

## 2025-05-18 - Accessibility on Responsive Dock Controls
**Learning:** Icon-only and responsive buttons that hide text labels on smaller screens (like `<span className="hidden md:inline">`) require explicit `aria-label` attributes to ensure screen readers provide clear context in all viewport sizes.
**Action:** Always include explicit `aria-label` on action buttons with hidden text spans or icon-only layouts.
