# GHIST: Structured Analysis

> **Paper:** Spatial gene expression at single-cell resolution from histology using deep learning with GHIST
> **Published:** 2024 Nature Methods
> **Authors:** Xiaohang Fu et al.
> **DOI:** 10.1038/s41592-025-02795-z
> **Code:** Not available at time of benchmarking assessment

---

## 1. Datasets

### Training Data
| Dataset | Tissue/Organ | Platform | Samples/Cells | Genes | Resolution |
|---------|-------------|----------|---------------|-------|------------|
| BreastCancer1 | Breast cancer | Xenium (10x) | ~80,000 cells | 280 | Single-cell |
| BreastCancer2 | Breast cancer | Xenium (10x) | ~80,000 cells, 850M pixels | 280 | Single-cell |
| BreastCancerILC | Breast cancer (ILC) | Xenium (10x) | - | 280 | Single-cell |
| BreastCancerIDC | Breast cancer (IDC) | Xenium (10x) | - | 280 | Single-cell |
| HER2ST | Breast cancer (HER2+) | ST (legacy) | 36 samples, 8 patients | 785 | Spot-level |

### Evaluation Data
| Dataset | Tissue/Organ | Platform | Samples | Purpose |
|---------|-------------|----------|---------|---------|
| BreastCancer1 | Breast cancer | Xenium | 1 sample | External test (cross-sample) |
| BreastCancer2 | Breast cancer | Xenium | 5-fold CV | Internal CV (spatial splits) |
| HER2ST | Breast cancer | ST | 4-fold CV | Internal CV (patient-level splits) |
| Melanoma | Skin | Xenium | 5-fold CV | Cross-tissue evaluation |
| Lung adenocarcinoma | Lung | Xenium | 5-fold CV | Cross-tissue evaluation |

### External / Downstream Application Data
- **TCGA-BRCA**: 92 HER2+ subtype WSIs (~63 million cells total) for survival analysis and pseudobulk correlation
- **Single-cell RNA-seq reference**: Breast cancer reference from Human Cell Atlas / CZI CELLxGENE for cell-type information (not required to be matched to input H&E)

---

## 2. Innovation Points

1. **Single-cell resolution gene expression prediction from H&E**: First method to predict spatially resolved gene expression at single-cell (not spot) resolution directly from H&E images, by leveraging subcellular spatial transcriptomics (Xenium) as training data.

2. **Multitask learning with four biological information layers**: Jointly learns interdependencies between (i) cell type, (ii) neighborhood composition, (iii) cell nucleus morphology, and (iv) single-cell RNA expression via four prediction heads with biologically informed loss functions.

3. **Neighborhood composition-based cell type recovery**: Uses estimated neighborhood composition to correct for morphologically ambiguous cell types (e.g., B cells vs. T cells), recovering minority cell types that the model would otherwise miss.

4. **Cell-type-specific expression prediction**: Predicts gene expression via linear regression of average cell-type profiles rather than direct regression, ensuring biologically meaningful expression patterns consistent with cell identity.

### Architecture Summary
- **Input:** 256x256 H&E image patches
- **Backbone:** UNet3+ for nuclei segmentation and feature extraction (trained from scratch, He initialization)
- **Key module:** Four prediction heads (morphology/segmentation, cell-type classification, neighborhood composition, gene expression) with cross-head feature sharing and biologically informed losses (KL divergence for neighborhood, cross-entropy for cell type, cosine similarity for embedding consistency)
- **Output:** Per-cell gene expression (n_cells x n_genes) + cell type labels + cell locations
- **Training strategy:** End-to-end, 50 epochs, AdamW optimizer (lr=0.001), batch size 8; scRNA-seq reference provides cell-type labels during training

---

## 3. Evaluation Methods

### Metrics Used
| Metric | Full Name | What it Measures |
|--------|-----------|-----------------|
| PCC | Pearson Correlation Coefficient | Linear correlation between predicted and ground-truth gene expression per gene |
| SSIM | Structural Similarity Index | Spatial structural similarity of expression patterns |
| RMSE | Root Mean Squared Error | Magnitude of prediction errors |
| C-index | Concordance Index | Discriminatory power of survival models using predicted expression |
| Log-rank P | Log-rank test P value | Significance of survival stratification between risk groups |
| F1 | F1 Score | Cell-type classification accuracy |

### Baselines / Compared Methods
| Method | Year | Key Difference |
|--------|------|---------------|
| ST-Net | 2020 | DenseNet-121, spot-level, ImageNet pretrained |
| HisToGene | 2021 | Transformer-based, spot-level |
| Hist2ST | 2022 | Transformer + CNN, spot-level |
| DeepPT | 2022 | ResNet-50, spot-level |
| DeepSpaCE | 2022 | VGG16, spot-level |
| GeneCodeR | 2023 | Non-deep-learning, coordinate descent |
| THItoGene | 2023 | Capsule network + ViT + GAT |
| BLEEP | 2024 | Contrastive learning, spot-level |
| iStar | 2024 | Hierarchical ViT, super-resolution |

### Evaluation Protocol
- **Cross-validation:** 5-fold spatial CV for Xenium datasets (horizontal sections); 4-fold patient-level CV for HER2ST
- **Gene selection:** 280 Xenium panel genes; 785 genes for HER2ST; top 20 SVGs and HVGs for focused evaluation
- **Downstream evaluation:** Survival analysis on 92 TCGA-BRCA HER2+ WSIs using Cox proportional hazard model with 5,000 repeated 3-fold CV
- **Statistical testing:** Two-sided log-rank test for survival stratification

---

## 4. Prediction Accuracy

### Main Results
| Task / Dataset | Metric | GHIST | Best Baseline | Improvement |
|---------------|--------|-------|---------------|-------------|
| HER2ST (HVGs) | PCC | 0.20 | iStar (next best) | Highest among all methods |
| HER2ST (SVGs) | PCC | 0.27 | iStar (next best) | Highest among all methods |
| HER2ST (HVGs) | SSIM | 0.17 | - | Highest |
| HER2ST (SVGs) | SSIM | 0.26 | - | Highest |
| HER2ST (all genes) | RMSE | 0.20 | - | - |
| HER2ST (SVGs) | RMSE | 0.22 | - | - |
| TCGA-BRCA HER2+ survival | Log-rank P | 0.017 | Hist2ST: 0.00084 | GHIST significant; Hist2ST also significant |

### Key Numerical Findings
- PCC = 0.20 for HVGs and 0.27 for SVGs on HER2ST (785 genes), outperforming all 8 compared spot-based methods
- Top 5 correlated genes on HER2ST: GNAS (0.32), FASN (0.31), SCD (0.26), CLDN4 (0.25), MYL12B (0.24)
- GHIST outperformed iStar on pseudospot-based comparison using BreastCancer2 for top 20 SVGs
- Survival analysis: GHIST achieved significant risk stratification (log-rank P = 0.017) on TCGA-BRCA HER2+ patients

### Downstream / Clinical Results
- Survival stratification on 92 TCGA-BRCA HER2+ patients: significant separation of high-risk vs. low-risk groups (P = 0.017)
- Only GHIST and Hist2ST achieved significant log-rank P values among all compared methods
- Inference on 92 TCGA-BRCA WSIs completed in ~20 hours (~63 million cells)

### Limitations Noted by Authors
- Cell-type discrimination is limited by gene panel design (e.g., 280-500 genes may not include key marker genes like P63 for myoepithelial cells)
- Performance depends on availability of high-quality subcellular spatial transcriptomics training data
- Currently demonstrated primarily on breast cancer; expansion to other cancer types depends on training data availability

---

*Generated by `/paper-analysis` on 2026-04-08*
