# Palette's Journal - Critical UX & Accessibility Learnings

## 2026-10-07 - Accessible Icon Toggles in Dual Dark/Crimson Themes
**Learning:** Responsive UI components like floating docks hide text labels on mobile viewports (`hidden md:inline`), effectively rendering buttons as icon-only. Without explicit `aria-label` and `aria-pressed` attributes, screen readers cannot announce button functions or toggle states. Furthermore, in custom high-contrast modes (e.g. OLED Night Crimson), focus rings must use theme-matched ring colors (`focus-visible:ring-red-400` vs `focus-visible:ring-emerald-400`).
**Action:** Always provide explicit `aria-label`, `aria-pressed`, and theme-aware `focus-visible:ring-2` focus indicators on responsive dock or toolbar icon buttons.
