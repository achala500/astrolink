# Bolt's Journal - Critical Performance Learnings

## 2026-10-16 - Subsampled Noise Estimation & Pre-extracted Image Normalization for Star Registration
**Learning:** Computing exact percentiles (`np.percentile`) and median/MAD statistics on full-resolution multi-megapixel floating-point images in `alignment.py` caused significant CPU sorting overhead. Using strided subsampling (`[::4, ::4]` for images >= 512x512) speeds up statistical noise thresholding by >10x while maintaining statistical accuracy. Furthermore, passing pre-extracted uint8 normalized frames to `count_stars` in `align_frame` avoids duplicate `_extract_gray_u8` calls.
**Action:** When calculating global background statistics (percentile, median, MAD) on large 2D image arrays, always subsample with strided slices before passing to NumPy reduction functions, and pass already-computed uint8 normalized frames across pipeline processing gates.
