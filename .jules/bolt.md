## 2026-03-31 - Fast-Path In-Place Welford Stacking
**Learning:** In streaming image frame accumulation using NumPy (e.g. Welford's algorithm), replacing general masked conditional updates (`np.where`) with a fast-path in-place update when all pixels are valid (`np.all(valid)`) yields a ~1.8-1.9x speedup per frame by avoiding redundant full-image temporary allocations and elementwise conditional branches.
**Action:** When implementing pixel-level array accumulation pipelines, always check for the unmasked/clean frame fast-path before applying masking logic.
