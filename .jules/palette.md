## 2025-05-18 - Responsive Dock Controls Accessibility
**Learning:** Navigation controls that hide text labels on smaller viewports (`hidden md:inline`) become pure icon-only buttons on mobile devices and screen readers without `aria-label` attributes.
**Action:** Always provide explicit `aria-label` attributes and focus-visible indicators (`focus-visible:ring-2`) on action buttons with hidden textual labels or icons.
