## 2026-10-23 - Avoid Redundant Grayscale Normalization and Full-Array Percentile Extraction in Alignment

**Learning:** During frame registration (`align_frame`), `_extract_gray_u8()` was executed 4 times per frame call (twice directly, and twice inside `count_stars()`). On float32 astrophotography images, each call computed `np.percentile()` across the full image array. Passing pre-extracted `u8` buffers to `count_stars(image, u8=ref_u8)` and using strided subsampling (`img[::4, ::4]`) for background statistics reduced alignment execution time by over 54% (from 345ms to 158ms per frame).

**Action:** When validating quality gates or feature tracking, pass pre-computed normalized `u8` arrays to downstream helpers, and use strided samples (`[::4, ::4]`) for global intensity percentile estimation on images $\ge 256\times 256$.
