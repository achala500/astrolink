## 2025-05-18 - ARIA Labels on Responsive Collapsing Icon Buttons
**Learning:** In compact dark-theme navigation docks with responsive CSS hiding text labels on smaller viewports (`hidden md:inline`), relying solely on tooltip `title` attributes leaves screen readers without accessible text when text spans collapse.
**Action:** Always provide explicit, concise `aria-label` attributes on icon-only and responsively collapsing action buttons.
