## 2026-10-26 - Crimson Mode Focus Ring & Disabled Button Tooltips
**Learning:** Icon-only dark-mode and night-crimson mode control docks often hide interactive states and disabled button explanations unless explicit focus-visible rings and disabled titles are attached to the element directly.
**Action:** Always pair `focus-visible:ring-2` with theme-aware colors (`focus-visible:ring-emerald-400` / `focus-visible:ring-red-500`) and explicit `aria-label` & disabled tooltips on icon buttons.
