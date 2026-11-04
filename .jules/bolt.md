# Bolt's Performance Journal

## 2026-11-04 - 1D Coordinate Broadcasting for 2D Polynomial Surface Evaluation
**Learning:** Evaluating a 2D bivariate polynomial surface across high-resolution image grids by allocating 2D meshgrids (`np.mgrid`) and building a full flattened `(H*W, N_terms)` column-stacked feature matrix allocates massive intermediate memory (~183 MB per channel on 2000x2000 images in float64) and creates a major CPU bottleneck in `np.column_stack` and matrix multiplication.
**Action:** Use 1D normalized coordinate vectors shaped `(1, W)` and `(H, 1)` and evaluate polynomial terms `c * (x_1d**i) * (y_1d**j)` directly into the `(H, W)` result array via NumPy broadcasting. This reduces intermediate memory from `O(H*W*N_terms)` to `O(H*W)` and approximately doubles execution speed.
