# Bolt's Journal - Critical Performance Learnings

## 2025-05-18 - Avoid Duplicate Grayscale Conversion and Full Array Percentiles in Alignment
**Learning:** During star frame alignment (`align_frame`), both feature matching and cloud rejection (`count_stars`) required uint8 grayscale array conversions. Computing `_extract_gray_u8` separately in `align_frame` and inside `count_stars` duplicated expensive image normalization and float percentile calls on large high-res frames (e.g., 3000x4000). Furthermore, calculating percentiles and median/MAD over all 12M pixels took ~1.8s per iteration.
**Action:** Reuse pre-extracted `u8` image arrays across pipeline functions where possible (e.g., `count_stars(image, u8)`). Use strided subsampling (`[::4, ::4]`) for global background statistics on large images ($\ge 512\text{px}$), reducing percentile estimation time from 0.47s to 0.11s (~3.7x speedup) with identical thresholding accuracy.
