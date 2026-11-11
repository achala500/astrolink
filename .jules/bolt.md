# Bolt's Performance Journal

## 2026-11-11 - Avoid 2D meshgrids and feature matrices when evaluating fitted 2D polynomial surfaces
**Learning:** Evaluating a fitted 2D polynomial background model (degree 2) on full-resolution camera frames (e.g. 12MP-24MP) via `np.mgrid` and an explicit feature matrix `(H*W, 6)` allocates hundreds of megabytes in temporary arrays and requires tens of seconds of dense matrix-vector multiplications. By leveraging NumPy 1D coordinate broadcasting `(1, W)` and `(H, 1)` and Horner-factored evaluation, intermediate arrays are minimized and evaluation speed improves by ~10x while remaining numerically identical.
**Action:** When evaluating smooth 2D spatial models (like skyglow background or vignetting), always prefer 1D orthogonal coordinate broadcasting over building full 2D coordinate meshgrids and dense polynomial feature matrices.
