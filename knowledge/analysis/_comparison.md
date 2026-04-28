# Paper Comparison

*Generated on 2026-04-08*

## Overview

| Aspect | GHIST | iSCALE | HistoCell | MAD |
|--------|-------|--------|-----------|-----|
| **Year** | 2024 | 2025 | 2025 | 2026 |
| **Journal** | Nature Methods | Nature Methods | Nature Communications | arXiv |
| **Resolution** | Single-cell | 8um superpixel (~single-cell) | Single-nucleus | Single-cell |
| **Input** | H&E + scRNA-seq ref | H&E + daughter ST captures | H&E (weakly supervised) | Fluorescence/H&E microscopy |
| **Platform** | Xenium, ST (legacy) | Visium, Xenium (benchmarking) | Not specified (multiple) | Xenium, Cell Painting, H&E |
| **# Genes predicted** | 280 (Xenium panel) / 785 (HER2ST) | 377 (Xenium) / 3,000+ HVGs (Visium) | Not reported (cell types/states, not genes) | 100 (top variable genes) |
| **Key innovation** | Multitask learning across 4 biological layers | Multi-capture integration for large tissues | Weakly-supervised cell spatial profiles | Dual-view self-distillation (morph + microenv) |
| **Primary metric** | PCC, SSIM | RMSE, SSIM, Pearson, Spearman | Cell type/state accuracy | ARI, PCC, Recall@K |
| **Best score** | PCC=0.27 (SVGs, HER2ST) | PCC=0.50 (MYH11, gastric) | SOTA (details in full paper) | 87% genes best predicted vs. baselines |
| **Code available** | No (at time of assessment) | Yes (GitHub) | Not reported | No |

## Dataset Overlap
- **Xenium platform**: Used by GHIST (breast cancer), iSCALE (gastric benchmarking ground truth), and MAD (lung, lymph node, ovarian; also HEST-1K lung for gene expression)
- **H&E images**: All four methods use H&E as input (MAD additionally supports fluorescence)
- **TCGA**: GHIST applies to 92 TCGA-BRCA WSIs for survival analysis; others do not use TCGA
- **No direct dataset overlap**: Each paper uses different tissue types and cohorts -- GHIST focuses on breast cancer, iSCALE on gastric + MS brain, HistoCell on multiple cancers, MAD on lung + ovarian + cell culture
- **HER2ST dataset**: Only used by GHIST; compared against same baselines (ST-Net, HisToGene, etc.) evaluated in the benchmarking paper by Chan et al.

## Architectural Comparison
GHIST and MAD both operate at single-cell resolution but take fundamentally different approaches: GHIST uses a supervised multitask UNet3+ trained end-to-end from scratch with biologically informed losses connecting cell type, neighborhood, morphology, and expression, while MAD uses a self-supervised ViT-L backbone pretrained via DINO-style distillation with frozen embeddings and lightweight downstream decoders. iSCALE takes a unique approach by integrating multiple small ST captures onto a large H&E image using a feedforward neural network, prioritizing tissue scale over architectural sophistication. HistoCell is weakly-supervised, predicting cell types, states, and spatial networks rather than gene expression directly. MAD is the only method designed as a general pretraining strategy applicable across imaging modalities (fluorescence and H&E), while the others are task-specific pipelines.

## Performance Comparison
Direct head-to-head comparison is limited since the papers use different datasets and tasks:
- **GHIST vs. iStar**: GHIST outperformed iStar on HER2ST (spot-level) and BreastCancer2 (pseudospot). iSCALE also outperformed iStar across all metrics on gastric cancer benchmarking. This positions both GHIST and iSCALE as improvements over iStar, though in different contexts (breast vs. gastric tissue).
- **MAD vs. foundation models**: MAD outperformed UNI (pathology foundation model) and CellDINO with matched parameters on H&E gene expression prediction, demonstrating that cell-centric pretraining beats larger-scale generic pretraining.
- **Gene expression prediction**: GHIST reports PCC = 0.20-0.27 (HVGs/SVGs) on breast cancer ST data; iSCALE reports PCC up to 0.50 on individual genes (gastric cancer Xenium); MAD achieves best PCC for 87/100 genes on lung Xenium. These numbers are not directly comparable due to different gene sets, platforms, and tissues.
- **Unique strengths**: Only GHIST demonstrates clinical survival prediction (TCGA-BRCA); only iSCALE handles tissues exceeding standard capture areas; only MAD works across imaging modalities; only HistoCell predicts cell states and spatial networks (not gene expression).
