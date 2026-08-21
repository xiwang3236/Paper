# MAD: Structured Analysis

> **Paper:** MAD: Microenvironment-Aware Distillation -- A Pretraining Strategy for Virtual Spatial Omics from Microscopy
> **Published:** 2026 arXiv
> **Authors:** Jiashu Han et al.
> **DOI:** 10.48550/arXiv.2603.13401
> **Code:** Not available

---

## 1. Datasets

### Training Data (Pretraining)
| Dataset | Tissue/Organ | Platform | Samples/Cells | Genes | Resolution |
|---------|-------------|----------|---------------|-------|------------|
| Human Protein Atlas (v16) | Cell culture | 4-channel fluorescence | ~70,000 cells, 8 classes | - | Subcellular |
| Cell Painting (LINCS) | Cell culture | 4-channel fluorescence | ~1,000,000 cells, ~100 classes | - | Subcellular |
| Cell Painting (JUMP) | Cell culture | 4-channel fluorescence | ~1,000,000 cells, 9 classes | - | Subcellular |
| Human lung cancer | Lung cancer tissue | Xenium (10x), 4-channel stains | ~160,000 cells, 24 classes | - | Subcellular |
| Human lymph node | Lymph node tissue | Xenium (10x), 4-channel stains | ~700,000 cells, 28 classes | - | Subcellular |
| Human ovarian cancer | Ovarian cancer tissue | Xenium (10x), 4-channel stains | ~400,000 cells, 18 classes | - | Subcellular |
| HEST-1K (subset) | Multiple organs | H&E | 65 WSIs with cell segmentation masks | - | Subcellular |

### Evaluation Data
| Dataset | Tissue/Organ | Platform | Samples | Purpose |
|---------|-------------|----------|---------|---------|
| Human ovarian cancer | Ovarian cancer | Xenium | ~400,000 cells | Ablation study (ARI for embedding quality) |
| 6 datasets above | Various | Fluorescence | Various | Cell subtyping benchmark |
| HEST-1K lung subset | Lung | H&E + Xenium | 18 tissues, ~50 million cells | Gene expression prediction from H&E |

### External / Downstream Application Data
- **HEST-1K lung tissues (20 slides)**: ~50 million cells with Visium HD or Xenium single-cell transcriptomics for gene expression prediction proof-of-concept
- **Gene expression prediction**: Top 100 most variable genes evaluated

### Reference Data
- LVD-142M pretrained weights for ViT-L backbone initialization
- UNI pathology foundation model (Mass-100K corpus) as comparison baseline
- CellDINO as comparison baseline for fluorescence microscopy

---

## 2. Innovation Points

1. **Dual-view joint self-distillation**: Novel four-way cross-entropy loss that aligns class tokens across morphology and microenvironment views from both teacher and student networks, learning unified cell-centric representations that capture both intrinsic cell features and tissue context simultaneously.

2. **Cell-centric pretraining from tissue images**: Instead of treating images as generic patches, MAD explicitly constructs morphological (segmented cell only) and microenvironmental (cell + neighborhood) image pairs for each indexed cell, encoding biological priors about cellular identity into the pretraining strategy.

3. **Outperforms foundation models with less data**: Despite using only 307M parameters and modest pretraining datasets, MAD outperforms foundation models (UNI, CellDINO) pretrained on substantially larger datasets (Mass-100K), demonstrating that cell-centric inductive biases are more important than dataset scale.

4. **Modality-agnostic framework**: Works across fluorescence microscopy (4-channel stains) and standard H&E histology, with the same architecture handling different imaging modalities by simply varying the input channels.

### Architecture Summary
- **Input:** Paired morphological (segmented cell) and microenvironmental (cell + neighborhood) image crops
- **Backbone:** ViT-Large (ViT-L/16), 307M parameters, initialized with LVD-142M pretrained weights
- **Key module:** Dual-view joint self-distillation with four-way cross-entropy loss; teacher-student framework with EMA updates; concatenated class tokens from both views form 2048-dim embedding
- **Output:** 2048-dimensional MAD embedding per cell (concatenation of 1024-dim morphology + 1024-dim microenvironment class tokens)
- **Training strategy:** Self-supervised pretraining (DINO-based); ~6 hours/epoch on 2x A6000 GPUs for 100M cells; convergence in ~15 epochs; frozen backbone with lightweight MLP decoders for downstream tasks

---

## 3. Evaluation Methods

### Metrics Used
| Metric | Full Name | What it Measures |
|--------|-----------|-----------------|
| ARI | Adjusted Rand Index | Embedding quality for cell type segregation in UMAP |
| Recall@K | Recall at K | Cross-view retrieval consistency (K=1,5,10) |
| PCC | Pearson Correlation Coefficient | Gene expression prediction accuracy |
| MAE | Mean Absolute Error | Absolute deviation in predicted expression |
| CCA | Canonical Correlation Analysis | Linear correlation between embedding spaces |
| F1 | F1 Score | Cell subtyping classification accuracy |

### Baselines / Compared Methods
| Method | Year | Key Difference |
|--------|------|---------------|
| ResNet-50 | 2016 | Supervised classification baseline |
| VAE | - | Self-supervised, single-view embedding |
| VQ-VAE | - | Discrete codebook latent space |
| CellDINO | 2025 | DINOv2-based, fluorescence-adapted, single-view |
| UNI | 2024 | ViT-L/16 pathology foundation model, pretrained on Mass-100K corpus |
| Morphology-only baseline | - | MAD with only cell-centered crops |
| Microenvironment-only baseline | - | MAD with only neighborhood crops |

### Evaluation Protocol
- **Ablation study:** Ovarian cancer dataset; ARI comparison between morphology-only (0.20), microenvironment-only (0.37), and full MAD (0.63)
- **Cell subtyping:** 6 datasets (3 cell culture + 3 tissue); lightweight MLP decoder on frozen MAD embeddings
- **Gene expression prediction:** HEST-1K lung subset; top 100 most variable genes; PCC per gene
- **Statistical testing:** Differential gene expression analysis and Gene Ontology enrichment on MAD-predicted vs. Xenium-measured expression

---

## 4. Prediction Accuracy

### Main Results
| Task / Dataset | Metric | MAD | Best Baseline | Improvement |
|---------------|--------|-----|---------------|-------------|
| Ovarian cancer (embedding quality) | ARI | 0.63 | Micro-only: 0.37, Morph-only: 0.20 | +70% over micro-only |
| H&E gene expression (lung, 100 genes) | % genes with best PCC | 87% | UNI/CellDINO (remaining 13%) | MAD best for 87/100 genes |
| Cell subtyping (6 datasets) | F1 / accuracy | SOTA across all | ResNet-50, VAE, CellDINO | Consistently top performance |

### Key Numerical Findings
- Embedding quality (ARI): Morphology-only = 0.20, Microenvironment-only = 0.37, MAD (dual-view) = 0.63 on ovarian cancer
- For 87% of top 100 variable genes in lung tissue, MAD achieved the most accurate expression predictions vs. all baselines
- Biologically relevant markers (SCGB3A2, SFTPC) among genes best predicted by MAD
- MAD outperforms UNI (pretrained on Mass-100K, substantially larger dataset) with matched model parameters
- Cross-view retrieval recall demonstrates strong alignment between morphological and microenvironmental embedding spaces
- Pretraining on 100M cells converges in ~15 epochs (~90 hours on 2x A6000)

### Downstream / Clinical Results
- Differential gene expression analysis: MAD-predicted expression recapitulates ground-truth differential expression patterns between cell populations
- Gene Ontology enrichment: Significantly differentially expressed genes from MAD predictions overlap with those from Xenium measurements
- MAD predicts absolute expression levels (not just relative trends), enabling direct comparison with molecular assay measurements

### Limitations Noted by Authors
- Improving generalizability across diverse tissue types, disease states, and imaging resolutions is future work
- Requires cell segmentation masks for pretraining (available for 65/1000+ WSIs in HEST-1K)
- Currently demonstrated on lung tissue for H&E; scaling to other organs pending
- Self-supervised pretraining requires substantial compute (~90 GPU-hours for 100M cells)

---

*Generated by `/paper-analysis` on 2026-04-08*
