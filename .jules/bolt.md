# Bolt's Journal - Critical Performance Learnings

## 2026-10-31 - Full-Resolution 2D Polynomial Surface Memory Spikes
**Learning:** Evaluating 2D polynomial surfaces across full-resolution frames by building full 2D coordinate meshgrids (`np.mgrid`) and stacking feature matrices (`_build_bivariate_poly_features`) consumes `O(H * W * terms)` memory (e.g., >277MB on a single 1500x1500 frame), causing latency bottlenecks and risking memory limits (>200MB ceiling).
**Action:** Use 1D coordinate broadcasting (`x_1d` of shape `(1, W)` and `y_1d` of shape `(H, 1)`) to directly accumulate polynomial terms in-place into the `(H, W)` surface without allocating 2D feature design matrices.
