## 2026-03-31 - High-Resolution Array Sorting in Pipeline Gates

**Learning:** Full-array sorting functions like `np.percentile()` on high-resolution float images (e.g., 2000x3000x3 float32 astronomical frames) consume hundreds of milliseconds per frame (~200ms per call). When called redundantly inside sub-exposure pipeline loops (such as during uint8 normalization and star counting in `alignment.py` and `gates.py`), total frame alignment overhead inflates by >600ms per frame. Subsampling large images (`img[::4, ::4]`) for percentile calculation achieves near-identical thresholding scaling in ~10ms while preserving pipeline accuracy.

**Action:** Always subsample multi-megapixel arrays when computing statistical percentiles or global background noise floors, and avoid redundant `_extract_gray_u8` or image normalizations by passing pre-converted uint8 buffers across pipeline stages.
