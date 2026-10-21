## 2026-10-21 - Accessible Toggle States & Screen-Reader Labels on Floating Floating Docks
**Learning:** Icon-only or combined icon-text buttons in persistent floating dock bars (like `Dock.jsx`) require both explicit `aria-label` text and dynamic `aria-pressed` state attributes for toggle filters so screen readers convey state accurately.
**Action:** When adding or updating action buttons or filter toggles in bottom floating docks, always include explicit `aria-label` and `aria-pressed={!!stateVariable}`.
