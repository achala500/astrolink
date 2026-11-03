# Bolt's Performance Journal

## 2026-11-03 - 2D Polynomial Surface Evaluation via 1D Coordinate Broadcasting
**Learning:** In astronomical light-pollution and background gradient extraction, evaluating a fitted bivariate polynomial surface across full sensor frames (e.g. 12MP-24MP DSLR images) using `np.mgrid` and `np.column_stack` for feature expansion allocates massive intermediate matrices (`full_features` of shape `(h*w, num_terms)` takes ~576MB of RAM for a 12MP frame) and takes >6s per channel. Evaluating terms directly via 1D coordinate broadcasting (`x_1d` shape `(1, w)` and `y_1d` shape `(h, 1)`) eliminates the intermediate full-resolution feature matrix, keeping memory peak under 50MB and accelerating evaluation by >25x.
**Action:** When evaluating separable 2D spatial models (polynomials, Gaussians, linear ramps) over regular grids, avoid generating 2D meshgrids or full feature matrices. Use 1D vector broadcasting over rows and columns.
