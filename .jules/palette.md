# Palette's Journal - Critical Learnings

## 2025-05-18 - Accessibility for Icon-Only Viewport & Dock Controls
**Learning:** Toolbar and Floating HUD components heavily rely on icon-only buttons with `title` attributes, which screen readers often ignore or fail to summarize properly. Adding explicit `aria-label` attributes ensures screen readers announce the action clearly without affecting visual layout.
**Action:** Always provide explicit `aria-label` attributes for icon-only action buttons in floating docks and viewports.
