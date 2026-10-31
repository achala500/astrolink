# Palette's Journal - Critical UX & Accessibility Learnings

## 2025-05-18 - Dual Dark & OLED Crimson Accessibility Pattern
**Learning:** In astronomical UI applications with high-contrast night vision modes (e.g. OLED Crimson), standard focus indicators (`focus-visible`) blend into dark backgrounds or distort night vision adaptation if rendered in generic browser blue/white. Using context-aware focus rings (`focus-visible:ring-emerald-400` in standard dark mode vs `focus-visible:ring-red-400` with black ring offsets in Crimson mode) preserves visual feedback and scotopic vision for keyboard-only observers in the field.
**Action:** When designing interactive controls for dark / night-adapted astronomer interfaces, always pair `aria-pressed` on toggles with dynamic `focus-visible` rings matching the active night theme palette.
