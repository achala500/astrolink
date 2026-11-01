# Palette UX & Accessibility Journal

## 2025-05-18 - Scotopic Vision Adaptation in Interactive Keyboard Focus Rings
**Learning:** In astronomical capture tools with dedicated night vision modes (such as OLED Crimson Mode), standard browser focus rings (blue/white/emerald) destroy dark adaptation and violate scotopic vision requirements during night observation sessions. Focus rings must adaptively match the active night vision theme (`focus-visible:ring-red-500` under Crimson mode vs `focus-visible:ring-emerald-400` in standard dark mode) while retaining clear contrast for keyboard and switch accessibility.
**Action:** When adding keyboard focus states (`focus-visible:outline-none focus-visible:ring-2`) to components, always conditionalize ring colors against `isCrimson` to preserve dark adaptation in the field.
