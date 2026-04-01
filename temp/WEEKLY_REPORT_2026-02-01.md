# Weekly Report: Spatial Omics Paper Search

**Period**: 2025-12-03 to 2026-02-01
**Generated**: 2026-02-01

## Summary Statistics

| Source | Total Found | Relevant (added) |
| --- | --- | --- |
| arXiv (7 days) | 2 | 1 |
| Journals (60 days) | 63 | 20 |
| **Total** | **65** | **21** |

- **6 papers** added to README.md (prediction methods)
- **15 papers** added to RELATED.md (ST analysis/tools)
- Remaining papers were biology applications using ST or unrelated

## Prediction Method Papers (README.md)

1. **HistoPrism** (2026-01-29 arXiv) — Pan-cancer transformer for pathway-level gene expression prediction from H&E. Introduces pathway-level benchmark shifting evaluation from gene-level variance to functional coherence.

2. **STimage** (2026-01-16 Nature Communications) — Predicts spatial gene expression and cell types from H&E with uncertainty quantification via ensemble foundation models. Validated across diverse platforms.

3. **Multimodal framework** (2026-01-16 NPJ AI) — Integrates WSI + ST to identify molecular mechanisms driving patient group-associated morphology. Applied to HER2+ breast cancer trastuzumab resistance.

4. **PathGen** (2025-12-31 Nature Communications) — Diffusion-based crossmodal gene expression generation from histopathology for multimodal AI. Code: [GitHub](https://github.com/Samiran-Dey/PathGen).

5. **SpatialEx** (2025-12-17 Nature Methods) — High-parameter spatial multi-omics through histology-anchored integration. Foundation model + hypergraph learning for single-cell omics prediction.

6. **mSTAR** (2025-12-12 Nature Communications) — Multimodal knowledge-enhanced pathology foundation model integrating slides, reports, and gene expression.

## Notable ST Analysis/Tool Papers (RELATED.md)

### Foundation Models & Methods
- **Novae** (2025-12-10 Nature Methods) — Graph-based foundation model for spatial domain detection. [GitHub](https://github.com/MICS-Lab/novae)
- **CellSAM** (2025-12-08 Nature Methods) — Universal foundation model for cell segmentation. [Web](https://cellsam.deepcell.org/)

### Spatial Reconstruction & Imputation
- **PanoSpace** (2026-01-06 Nature Computational Science) — Reconstructs continuous single-cell ST maps from low-res ST + histology + scRNA
- **SpatialZ** (2025-12-31 Nature Methods) — Bridges planar ST to 3D cell atlases via virtual slice generation
- **PASTA** (2025-12-16 Nature Communications) — Pathway-specific gene expression imputation in ST

### Multi-omics Integration
- **MAGPIE** (2026-01-07 Nature Communications) — Co-registers ST, metabolomics (MALDI/DESI), and morphology

### Spatial Domain Detection & Clustering
- **STransfer** (2026-01-27 Bioinformatics) — Transfer learning GCN for ST clustering. [GitHub](https://github.com/Saki-JSU/Publications/tree/main/STransfer)
- **SpatialRNA** (2026-01-01 Bioinformatics) — GNN for single-molecule ST. [GitHub](https://github.com/ruqianl/spatialrna)
- **STAHD** (2026-01-01 Bioinformatics) — Scalable spatial domain detection in high-res ST. [GitHub](https://github.com/Little-Eel/STAHD)

### Other Tools
- **CCCvelo** (2026-01-05 Nature Computational Science) — Cell state transitions driven by cell-cell communication
- **FastCCC** (2025-12-13 Nature Communications) — Permutation-free cell-cell communication analysis
- **SpaceBar** (2025-12-18 Nature Methods) — Clone tracing with imaging-based ST
- **Spider** (2026-01-01 Bioinformatics) — Framework for simulating ST data. [GitHub](https://github.com/YANG-ERA/Spider)
- **AdaSlide** (2025-12-03 Nature Communications) — Adaptive RL-based compression for gigapixel WSIs
- **SIDISH** (2025-12-10 Nature Communications) — Integrates scRNA + bulk to identify high-risk cells

## Biology Application Papers (not added)

The remaining ~44 journal papers were biology/clinical studies that used spatial transcriptomics as a tool but did not develop new computational methods. Topics included:
- Cancer microenvironment profiling (glioblastoma, lung, breast, ovarian, pancreatic)
- Developmental biology (brown adipose tissue, cortical interneurons)
- Inflammatory disease (colitis, atherosclerosis, pulmonary fibrosis)
- Drug resistance mechanisms (trastuzumab, RAS inhibitors, immune checkpoint)
- Immunology (immune cell dynamics, autoantibodies)

These were excluded as they do not introduce new spatial omics prediction or analysis methods.
