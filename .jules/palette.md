# Palette's Journal - Critical UX & Accessibility Learnings

## 2026-11-06 - Dark Adaptation & Scotopic Focus Ring Theming
**Learning:** In astronomical field tools with OLED dark adaptation modes (like AstroLink's OLED Crimson mode), standard browser or high-contrast white focus indicators destroy astronomers' rhodopsin dark adaptation. Interactive focus indicators must dynamically adjust their hue based on active dark-adaptation mode: `focus-visible:ring-emerald-400` in standard dark mode versus `focus-visible:ring-red-500` in Crimson mode.
**Action:** When adding keyboard accessibility and focus styles to interactive controls, always pair `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-black` with mode-conditioned ring colors (`isCrimson ? 'focus-visible:ring-red-500' : 'focus-visible:ring-emerald-400'`) and provide descriptive ARIA labels for icon-only action triggers.
