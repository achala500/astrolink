## 2025-05-18 - 1D Coordinate Broadcasting for Polynomial Surface Evaluation
**Learning:** Evaluating 2D polynomial surface basis terms on high-resolution images by creating full 2D meshgrids (`np.mgrid`) and building a massive `(H*W, N)` feature matrix causes significant memory allocations and slow matrix multiplications.
**Action:** Use 1D coordinate vectors (`x_1d` shape `(1, W)` and `y_1d` shape `(H, 1)`) with NumPy outer broadcasting to accumulate polynomial terms directly into the surface array.
