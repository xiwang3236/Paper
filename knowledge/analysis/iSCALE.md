# iSCALE: Structured Analysis

> **Paper:** Scaling up spatial transcriptomics for large-sized tissues: uncovering cellular-level tissue architecture beyond conventional platforms with iSCALE
> **Published:** 2025 Nature Methods
> **Authors:** Amelia Schroeder et al.
> **DOI:** 10.1038/s41592-025-02770-8
> **Code:** [iSCALE](https://github.com/amesch441/iSCALE)

---

## 1. Datasets

### Training Data
| Dataset | Tissue/Organ | Platform | Samples/Cells | Genes | Resolution |
|---------|-------------|----------|---------------|-------|------------|
| Gastric Cancer Tumor | Gastric cancer | Xenium (10x) | Full Xenium slide (12mm x 24mm), 5 pseudo-Visium daughter captures (3.2mm x 3.2mm each) | 377 | 8 um superpixels |
| Normal Gastric 1 (N1) | Normal gastric | Xenium (10x) | 10-11 pseudo-Visium daughter captures (2mm x 2mm each) | 377 | 8 um superpixels |
| Normal Gastric 2 (N2) | Normal gastric | Xenium (10x) | 8 pseudo-Visium daughter captures (2mm x 2mm each) | 377 | 8 um superpixels |
| MS Brain Sample 1 | MS brain | Visium (10x) | 11 daughter captures, 36,912 spots, 2,013,871 superpixels | 3,000 HVGs + 145 markers | 8 um superpixels |
| MS Brain Sample 2 | MS brain | Visium (10x) | 6 daughter captures, 2,042,781 superpixels | - | 8 um superpixels |

### Evaluation Data
| Dataset | Tissue/Organ | Platform | Samples | Purpose |
|---------|-------------|----------|---------|---------|
| Gastric Cancer Tumor | Gastric cancer | Xenium ground truth | 1 sample (1,971,625 superpixels) | In-sample benchmarking (500 gene-wise comparisons) |
| Normal Gastric 2 | Normal gastric | Xenium ground truth | 1 sample (1,352,947 superpixels) | In-sample + out-of-sample prediction |
| MS Brain Sample 2 | MS brain | IHC (MOG, CD68) | 1 sample | Out-of-sample prediction, IHC validation |

### External / Downstream Application Data
- **MS Brain Sample 2**: Out-of-sample prediction using model trained on Sample 1 (different lesion characteristics from same brain)
- **IHC staining on adjacent sections**: MOG and CD68 markers for validating predicted gene expression in MS samples

### Reference Data
- Single-nucleus RNA-seq from same MS brain for cell type marker selection (145 markers)
- Gastric tumor scRNA-seq from Cheng et al. (used as reference for RedeHist comparison)

---

## 2. Innovation Points

1. **Multi-capture integration for large tissues**: Novel framework that integrates gene expression from multiple small "daughter" ST captures onto a large "mother" H&E image, overcoming the capture area limitation of all commercial ST platforms (6.5mm x 6.5mm for Visium vs. tissues up to 25mm x 75mm).

2. **Semi-automatic daughter capture alignment**: Spatial-clustering-guided, human-in-the-loop alignment of daughter captures onto the mother image using key point detection, achieving 99% alignment accuracy.

3. **Hierarchical histological feature extraction**: Extracts both local (16px) and global (256px) tissue structure features from the mother H&E image, combining fine cellular details with broader tissue architecture for prediction.

4. **Out-of-sample prediction capability**: Can predict gene expression in entirely new tissue sections using only their H&E images, trained from a different sample's daughter captures -- demonstrated across MS samples with distinct pathology.

5. **Integrated pipeline from prediction to annotation**: End-to-end workflow from gene expression prediction to automatic cell type annotation and tissue segmentation using a percentile-based scoring approach.

### Architecture Summary
- **Input:** Large H&E mother image + aligned daughter ST captures from adjacent sections
- **Backbone:** Feedforward neural network for gene expression prediction; hierarchical tiling (16px, 256px) for feature extraction
- **Key module:** Multi-capture data integration with batch correction (Scanorama) + spatial smoothing across captures; semiautomatic alignment algorithm
- **Output:** Super-resolution gene expression per 8um x 8um superpixel + cell type annotations + tissue segmentation clusters
- **Training strategy:** Supervised, using integrated ST data from aligned daughter captures as labels

---

## 3. Evaluation Methods

### Metrics Used
| Metric | Full Name | What it Measures |
|--------|-----------|-----------------|
| RMSE | Root Mean Squared Error | Prediction accuracy (in-sample, values normalized to [0,1]) |
| SSIM | Structural Similarity Index | Spatial structural similarity (in-sample) |
| PCC | Pearson Correlation | Linear correlation at multiple resolutions (8, 16, 32, 64 um) |
| Spearman r | Spearman Correlation | Rank-based correlation (out-of-sample, magnitude-independent) |
| Chi-squared | Chi-squared statistic | Concordance of binarized expression patterns (expressed/not) |
| ARI | Adjusted Rand Index | Segmentation agreement between in-sample and out-of-sample |

### Baselines / Compared Methods
| Method | Year | Key Difference |
|--------|------|---------------|
| iStar | 2024 | Single daughter capture at a time; hierarchical ViT; no multi-capture integration |
| RedeHist | 2024 | Requires scRNA-seq reference; single capture at a time |

### Evaluation Protocol
- **In-sample:** Top 100 HVGs evaluated at 8um resolution (gastric cancer: 500 gene-wise comparisons across 1,971,625 superpixels)
- **Out-of-sample:** Spearman correlation and chi-squared concordance (Normal 1 train -> Normal 2 test; MS Sample 1 train -> MS Sample 2 test)
- **IHC validation:** MOG and CD68 staining on adjacent tissue sections compared with predicted binarized gene expression
- **Pathologist annotation:** Manual tissue region annotation compared with iSCALE segmentation

---

## 4. Prediction Accuracy

### Main Results
| Task / Dataset | Metric | iSCALE | Best Baseline (iStar) | Notes |
|---------------|--------|--------|----------------------|-------|
| Gastric cancer (MYH11) | PCC (8um) | 0.5037 | Best single capture: 0.4833 (D3) | iSCALE-Seq consistently outperforms any single iStar capture |
| Gastric cancer (TFF2) | PCC (8um) | 0.3868 | Best: 0.2513 (D1) | +54% over best iStar capture |
| Gastric cancer (ACTA2) | PCC (8um) | 0.2703 | Best: 0.2233 (D4) | +21% improvement |
| Normal gastric out-of-sample | ARI | 0.74 | - | Segmentation agreement between in-sample and out-of-sample |
| Normal gastric out-of-sample (64um) | Spearman | ~0.45 (50% genes above) | - | Out-of-sample, magnitude unknown |

### Key Numerical Findings
- iSCALE-Seq outperformed all individual iStar models (D1-D5) on RMSE, SSIM, and Pearson correlation for top 100 HVGs in gastric cancer
- Out-of-sample segmentation (Normal 1 -> Normal 2) achieved ARI = 0.74 agreement with in-sample segmentation
- 99/100 HVGs showed significantly concordant out-of-sample predictions (chi-squared test, Bonferroni-adjusted alpha = 0.05)
- iStar predictions were highly variable across daughter captures (e.g., TFF2 PCC ranged from 0.09 to 0.25 across D1-D5); iSCALE was consistently higher
- MS brain: iSCALE successfully detected white matter chronic active lesion core, active lesion rim, NAWM, and NAGM matching pathologist annotations

### Downstream / Clinical Results
- MS lesion characterization: iSCALE identified iron-rich microglia, foamy microglia, and T cells in active lesion rim
- CD68 expression correctly predicted along lesion rim border (undetected by iStar)
- MOG expression correctly predicted as negligible within demyelinated chronic active lesion core
- Out-of-sample MS prediction (Sample 1 -> Sample 2): Successfully mapped T cells to lesion rim and astrocytes to NAWM despite distinct pathology

### Limitations Noted by Authors
- Out-of-sample prediction is preliminary and limited by training data size
- Does not account for experimental design (strategic selection of daughter capture regions)
- Currently does not determine optimal number of captures needed
- Demonstrated primarily on Visium; adaptability to other platforms (CosMx, etc.) discussed but not demonstrated

---

*Generated by `/paper-analysis` on 2026-04-08*
