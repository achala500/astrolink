# Palette's Journal - Critical UX & Accessibility Learnings

## 2025-05-18 - Scotopic Vision Preservation in Keyboard Navigation
**Learning:** In astronomical field software with an OLED Crimson (Astro Red) night mode, standard bright focus indicators (e.g. emerald, blue, or white outline rings) can destroy an astronomer's dark adaptation (scotopic vision). Interactive focus rings must adapt dynamically to active night vision themes (e.g. `focus-visible:ring-emerald-400` in standard dark mode versus `focus-visible:ring-red-500` in OLED Crimson mode).
**Action:** When styling keyboard focus rings for interactive controls, always condition the focus ring color on `isCrimson` to preserve dark adaptation while maintaining full keyboard accessibility.
