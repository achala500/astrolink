# Bolt's Performance Journal

Critical learnings only. No routine logs.

## 2026-11-07 - 1D Coordinate Broadcasting for 2D Polynomial Surface Evaluation
**Learning:** In astronomical image gradient subtraction (`backend/app/pipeline/gradient.py`), constructing a full-resolution 2D design matrix `(H*W, N_terms)` via `np.mgrid` and computing `features @ coeffs` creates massive transient memory allocations (>180MB per 1080p channel) and severe CPU cache thrashing. Evaluating the bivariate polynomial surface using 1D coordinate broadcasting (`x_powers` shape `(1, W)` and `y_powers` shape `(H, 1)`) precomputed once across color channels reduces transient allocations from ~180MB to 8.3MB (>95% reduction) and accelerates background model evaluation by ~4.4x without any loss in numerical precision.
**Action:** When evaluating fitted 2D separable functions or bivariate polynomials over 2D grids, broadcast 1D coordinate arrays `(H, 1) * (1, W)` instead of constructing full `(H*W, N)` feature matrices.
