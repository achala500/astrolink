# Bolt's Performance Journal

Critical learnings only. Format: `## YYYY-MM-DD - [Title]` followed by `**Learning:**` and `**Action:**`.

## 2026-11-05 - Avoid 2D Coordinate Meshgrid Feature Matrices for Surface Evaluation
**Learning:** In astronomical image processing (e.g. background gradient modeling), building full-resolution 2D polynomial feature matrices via `np.mgrid` and `np.column_stack` allocates massive transient arrays (~128MB per 1000x1000 frame) and triggers expensive matrix-vector products. 1D coordinate vectors (`x_1d` shape `(1, W)` and `y_1d` shape `(H, 1)`) allow NumPy broadcasting to directly compute polynomial terms into the output array with ~4MB allocation and a >10x speedup.
**Action:** When evaluating separable 2D analytical models or polynomials across an entire image grid, use 1D broadcasting coordinate vectors instead of allocating full 2D coordinate meshgrids.
