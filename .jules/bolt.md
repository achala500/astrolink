# Bolt's Performance Journal

## 2026-11-10 - 2D Polynomial Surface Evaluation via 1D Broadcasting and Horner Factoring
**Learning:** In astronomical background gradient removal, evaluating a fitted 2D degree-2 polynomial surface across full sensor frames using `np.mgrid` and constructing full $(H \cdot W, 6)$ feature matrices creates massive transient memory allocations (~265MB per channel at 1080p, >750MB for RGB) and takes hundreds of milliseconds, easily exceeding the <200MB memory ceiling.
**Action:** Evaluate 2nd-degree bivariate polynomial surfaces using 1D coordinate vectors (`(1, w)` and `(h, 1)`) and Horner factoring (`c0 + y*(c1 + c3*y) + x*(c2 + c4*y + c5*x)`). NumPy's broadcasting performs the evaluation in a single pass in $O(1)$ memory per pixel, dropping 1080p RGB evaluation time by ~66% and eliminating all multi-hundred MB intermediate matrices.
