# Palette's UX & Accessibility Journal

## 2025-05-18 - Accessibility for Dark-Theme Icon-Only Controls
**Learning:** In high-contrast and crimson dark-mode interfaces with heavy icon-only action triggers (e.g. viewport tools, dock reset buttons, modal close handles), tooltips (`title`) alone fail screen reader navigation and accessibility standards without explicit `aria-label` attributes.
**Action:** Always complement `title` attributes on icon-only `<button>` elements with descriptive `aria-label` labels.
