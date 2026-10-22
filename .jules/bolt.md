## 2026-03-31 - Pre-extracted uint8 arrays and strided subsampling in image alignment
**Learning:** Re-extracting grayscale uint8 arrays and computing full-array percentile/median statistics on high-resolution images (>512x512) introduces multi-second bottlenecks per frame alignment. Passing pre-extracted `u8` arrays and strided subsampling (`[::4, ::4]`) for noise statistics cuts alignment overhead by >50%.
**Action:** Always accept optional pre-extracted `u8` arrays in quality gates/functions and use strided subsampling when computing global background statistics on large image arrays.
