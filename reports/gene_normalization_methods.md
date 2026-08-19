# Gene Normalization Methods Across Studies

## Summary Table

| Paper | Normalization Method | Applied To | Tools |
| --- | --- | --- | --- |
| [DeepSpaCE](https://www.nature.com/articles/s41598-022-07685-4) | SCTransform + min-max scaling | Target (gene expr) | Seurat |
| [BrST-Net](https://www.nature.com/articles/s41598-023-40218-1) | Vahadane stain norm + zero-mean/unit-variance | Input (images) | StainTools, PyTorch |
| [EGN](https://openaccess.thecvf.com/content/WACV2023/papers/Yang_Exemplar_Guided_Deep_Neural_Network_for_Spatial_Transcriptomics_Analysis_of_WACV_2023_paper.pdf) | Log transform + min-max norm | Target (gene expr) | - |
| [BLEEP](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1a1e21e1ee74ed0584e4f2ee34553bec-Abstract-Conference.html) | Total count norm + log norm + Harmony batch correction | Target (gene expr) | Scanpy, Harmony |
| [MagNet](https://arxiv.org/abs/2502.21011) | Proportional norm + log transform | Target (gene expr) | - |
| [CAMIL](https://www.nature.com/articles/s41467-024-45589-1) | Macenko color normalization | Input (images) | KatherLab pipeline |
| [STRank](https://github.com/naivete5656/STRank) | Rank-based loss (critiques standard normalization) | Target (gene expr) | CONCH |
| [DeepPT](https://www.biorxiv.org/content/10.1101/2023.05.07.539729v1) | "Normalized gene expression" (unspecified) | Target (gene expr) | - |
| [Benchmarking](https://www.nature.com/articles/s41467-025-56530-7) | Comparative study: notes normalization affects performance | Review | - |

## Details by Paper

### DeepSpaCE
- QC filter: spots with <1000 UMIs or <1000 genes removed
- **SCTransform** (Seurat) for variance-stabilizing normalization
- **Min-max scaling** applied after SCTransform

### BrST-Net
- **Vahadane stain normalization** via StainTools + Luminosity Standardizer for brightness
- Image tensors normalized to **zero mean, unit variance**
- Gene filtering: genes with mean expression = 0 removed; spots with >= 1000 reads kept

### EGN
- **Log transformation** followed by **min-max normalization** on target gene expression
- Applied to 250 genes with largest mean expression

### BLEEP
- **Total count normalization** per spot + **log normalization**
- HVG selection: union of top 1000 HVGs per slice (3,467 genes total)
- **Harmony** batch correction across slices
- Tools: Scanpy, Harmony

### MagNet
- **Proportional normalization** + **log transformation**
- Top 250 genes by average expression selected

### CAMIL (Marugoto pipeline)
- **Macenko color normalization** on H&E images
- Canny edge detection for background rejection
- Feature extraction via RetCCL (self-supervised ResNet50)

### STRank
- Argues **against** standard total-count normalization (converts discrete counts to continuous, compromising statistical properties)
- Proposes **rank-based loss functions** (PairSTRank, ListSTRank) as alternative to explicit normalization
- Uses correction term based on total expression level per spot

### Benchmarking Study
- Found that **method-specific normalization** (e.g., Hist2ST, HisToGene) can reduce correlation with original data
- Recommends focusing on HVGs/SVGs rather than all genes
- Identifies stain normalization as an open challenge

### Papers with No Explicit Normalization Described
- **VORTEX** — uses CONCH + scGPT foundation models (implicit representation handling)
- **HEX** — uses MUSK foundation model with Feature Distribution Smoothing (FDS)
- **GHIST** — preprocessing details not specified in available text
- **HistoCell** — not detailed in available text
- **Cell annotation framework** — not detailed in available text
