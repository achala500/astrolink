## 2026-10-11 - Image Alignment Redundant Grayscale Extraction & Subsampling
**Learning:** In `align_frame`, `_extract_gray_u8` was being called four times per frame alignment pass (twice directly and twice inside `count_stars`). Operating `np.percentile` over millions of un-subsampled pixels in float32 images created heavy overhead.
**Action:** Reuse pre-converted uint8 grayscale arrays when calling `count_stars` in `align_frame`, and use strided subsampling `[::4, ::4]` for global percentile/median statistics on images >=512x512.
