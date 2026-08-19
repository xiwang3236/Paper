# Studies Using Transformer Architecture

From the knowledge base (14 papers total), **4 studies** use transformer architecture as a core component.

---

| Method | Transformer Component | Prediction Target | Published | Code |
| --- | --- | --- | --- | --- |
| **EGN** | Vision Transformer (ViT) backbone with Exemplar Bridging blocks | Gene expression (250 genes) | WACV 2023 | [Repo](https://github.com/Yan98/EGN) |
| **MagNet** | Cross-attention layers + Transformer layers (combined with GAT) | Gene expression at HD resolution (8um) | 2025-02-28 arXiv | [Repo](https://github.com/Junchao-Zhu/MagNet) |
| **VORTEX** | ViT-based 3D encoder + CONCH (ViT foundation model) + scGPT (transformer foundation model) | 3D spatial transcriptomics | 2025-02-25 arXiv | TBA |
| **HEX** | MUSK pathology foundation model (transformer-based) + CODEX-guided co-attention (MICA) | 40 protein biomarkers | 2026-01-05 Nature Medicine | [Repo](https://github.com/lilab-stanford/HEX) |

---

## Paper Details

### 1. EGN (Exemplar Guided Network)
- **Link:** [Paper](https://openaccess.thecvf.com/content/WACV2023/papers/Yang_Exemplar_Guided_Deep_Neural_Network_for_Spatial_Transcriptomics_Analysis_of_WACV_2023_paper.pdf)
- **Architecture:** ViT backbone with interleaved Exemplar Bridging (EB) blocks that revise intermediate ViT representations using retrieved exemplars. StyleGAN-based unsupervised exemplar retrieval.
- **Input:** H&E patches | **Platform:** Spatial Transcriptomics (100um)

### 2. MagNet (Multi-Level Attention Graph Network)
- **Link:** [Paper](https://arxiv.org/abs/2502.21011)
- **Architecture:** Cross-attention layers merge multi-resolution features (bin/spot/region), then GAT + Transformer layers perform spatial-guided graph integration. Multi-head graph attention followed by transformer for neighborhood aggregation.
- **Input:** H&E (multi-resolution patches) | **Platform:** Visium HD (8um)

### 3. VORTEX (VOlumetrically Resolved Transcriptomics EXpression)
- **Link:** [Paper](https://arxiv.org/abs/2502.17761)
- **Architecture:** Three-stage pipeline using CONCH (ViT-based pathology foundation model) and scGPT (transformer-based single-cell foundation model) with contrastive alignment. ViT-based 3D encoder with depth aggregation. Dual attentional poolers inspired by CoCa.
- **Input:** H&E, microCT, OTLS | **Platform:** Visium, Spatial Transcriptomics

### 4. HEX (H&E to protein EXpression)
- **Link:** [Paper](https://www.nature.com/articles/s41591-025-04060-4)
- **Architecture:** Built on MUSK (transformer-based pathology foundation model) with regression head using Feature Distribution Smoothing. MICA companion framework uses CODEX-guided co-attention (transformer attention) for multimodal fusion.
- **Input:** H&E | **Platform:** CODEX (40-plex)
