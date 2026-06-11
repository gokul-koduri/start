# Hugging Face Model Publication Plan

> **Goal:** Publish startup-specific NLP models on Hugging Face Hub to establish market leadership,
> drive organic visibility, and create the "BERT of startup intelligence."
>
> **Date:** 2025-06-08
> **Status:** 📋 DRAFT — Ready for Review

---

## Executive Summary

After a comprehensive search of the Hugging Face Hub, **no existing models** cover:
- Startup failure prediction
- Startup-specific sentiment analysis
- Startup entity recognition (company, founder, funding, technology)

The closest existing models are generic financial sentiment classifiers (e.g., `FinancialBERT`) with 200K+ downloads, proving strong demand. By publishing startup-specific models, we capture a **blue ocean** niche.

### What We Already Have (Internal)

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| Sentiment Agent | `agents/sentiment_agent.py` | ✅ Working | VADER + Ollama LLM sentiment |
| Text Classifier | `nlp/text_classifier.py` | ✅ Working | Rule-based signal type + sentiment |
| NER Pipeline | `nlp/ner_pipeline.py` | ✅ Working | spaCy en_core_web_trf + custom EntityRuler |
| Embedding Generator | `nlp/embedding_generator.py` | ✅ Working | all-MiniLM-L6-v2 (384d) |
| ML Trainer | `agents/ml_trainer_agent.py` | ✅ Working | Random Forest + XGBoost failure prediction |
| ML Predictor | `agents/ml_trainer_agent.py` | ✅ Working | 70/30 ML+heuristic blending |
| Risk Scorer | `agents/risk_scorer_agent.py` | ✅ Working | Rule-based risk scoring |

### Gap → What Needs to Be Built for HuggingFace

| Model | Gap | Effort |
|-------|-----|--------|
| `startup-sentiment-v1` | Retrain BERT/DistilBERT on startup news data | Medium |
| `startup-ner-v1` | Convert spaCy EntityRuler patterns → proper HF token-classification model | Medium |
| `startup-failure-predictor-v1` | Convert scikit-learn pipeline → HF-compatible | Low |
| `startup-embedding-v1` | Fine-tune sentence-transformer on startup corpus | High |

---

## Phase 1: Data Preparation (Week 1)

### 1.1 Build Training Dataset

```
data/
├── hf_datasets/
│   ├── startup_sentiment/
│   │   ├── train.csv          # 5,000+ labeled startup news articles
│   │   ├── val.csv            # 1,000 validation
│   │   └── test.csv           # 1,000 test
│   ├── startup_ner/
│   │   ├── train.json         # BIO-tagged startup entity data
│   │   ├── val.json
│   │   └── test.json
│   └── startup_failure/
│       ├── train.csv           # Structured features + failure labels
│       ├── val.csv
│       └── test.csv
```

### 1.2 Data Sources (Already Available In-Project)

| Source | Records | Labels | Use Case |
|--------|---------|--------|----------|
| `failed_startups` DB table | ~500+ | failure_reason, sector, funding | Failure prediction, Sentiment |
| `news_articles` DB table | ~1000+ | title, summary, sentiment_score | Sentiment training |
| Seed data (`seed_data.py`) | ~100+ | Structured startup profiles | NER, Features |
| Kaggle startup datasets | ~50K+ | status, funding, sector | Failure prediction (external) |
| TechCrunch/HN collected data | Ongoing | Raw news text | Sentiment labeling |

### 1.3 Data Labeling Strategy

```
┌─────────────────────────────────────────────────────┐
│              DATA LABELING PIPELINE                  │
│                                                     │
│  1. AUTO-LABEL (VADER + Rules)                      │
│     → 80% coverage, fast                            │
│     → news_articles already have sentiment_score     │
│                                                     │
│  2. LLM-AUGMENT (Ollama)                            │
│     → Run deep sentiment on unlabeled articles       │
│     → Cost: ~$0 (local Ollama)                      │
│                                                     │
│  3. HUMAN REVIEW (Manual spot-check)                │
│     → Review 200-500 samples per class              │
│     → Fix mislabeled examples                       │
│                                                     │
│  4. DATASET PUBLISH ON HF                           │
│     → "startup-intelligence-dataset"                │
│     → Community can contribute                      │
└─────────────────────────────────────────────────────┘
```

---

## Phase 2: Model Training (Week 2-3)

### Model 1: `oip-startup-sentiment-v1`

**Task:** Text Classification (positive / negative / neutral)

```
Architecture:     DistilBERT-base-uncased (66M params)
Training Data:    5,000+ startup news articles
Base Model:       distilbert-base-uncased
Labels:           positive, negative, neutral
Expected F1:      0.85+
Inference Speed:  ~50ms per article
Model Size:       ~260MB

Classes:
  - positive: growth, funding, launch, expansion, acquisition
  - negative: failure, bankruptcy, layoff, shutdown, scandal
  - neutral: announcement, report, filing, hiring (no strong signal)
```

**Training Script Structure:**
```
scripts/
└── train_hf_models/
    ├── train_sentiment.py       # Fine-tune DistilBERT
    ├── train_ner.py             # Fine-tune BERT for NER
    ├── train_failure.py         # Export sklearn → HF format
    └── common/
        ├── data_loader.py
        └── metrics.py
```

### Model 2: `oip-startup-ner-v1`

**Task:** Token Classification (Named Entity Recognition)

```
Architecture:     BERT-base-uncased (110M params)
Training Data:    3,000+ annotated startup texts (BIO format)
Base Model:       dslim/bert-base-NER (pre-trained on general NER)
Labels:           STARTUP, PERSON, TECHNOLOGY, MARKET, FUNDING, LOCATION
Expected F1:      0.80+
Inference Speed:  ~80ms per article
Model Size:       ~420MB

Entity Types (Domain-Specific):
  - STARTUP:      "Stripe", "OpenAI", "Notion"
  - PERSON:       "Sam Altman", "Elon Musk"
  - TECHNOLOGY:   "PyTorch", "Kubernetes", "Rust"
  - MARKET:       "fintech", "SaaS", "healthtech"
  - FUNDING:      "$50M Series B", "seed round"
  - LOCATION:     "San Francisco", "Berlin"
```

### Model 3: `oip-startup-failure-predictor-v1`

**Task:** Tabular Classification (failure risk score)

```
Architecture:     Scikit-learn Pipeline (Random Forest + XGBoost ensemble)
Training Data:    1,000+ startups with known outcomes
Features:         sector_encoded, funding_bin, country_risk_index,
                  age_at_shutdown, is_manufacturing, has_funding,
                  funding_per_year
Output:           failure_probability (0.0 - 1.0)
Expected AUC:     0.80+

Export Format:
  - joblib (current) + ONNX (for HF compatibility)
  - Wrap in a HuggingFace sklearn Pipeline
```

### Model 4: `oip-startup-embedding-v1` (Stretch Goal)

**Task:** Sentence Embeddings fine-tuned for startup domain

```
Architecture:     all-MiniLM-L6-v2 fine-tuned (22M params)
Training Data:    10,000+ startup descriptions + news
Base Model:       sentence-transformers/all-MiniLM-L6-v2
Dimensions:       384
Use Case:         Semantic search, entity resolution, clustering
Expected Improvement: +10-15% on startup-specific similarity tasks
```

---

## Phase 3: Hugging Face Hub Setup (Week 3)

### 3.1 Organization Structure

```
HuggingFace Organization:  oip-startup-intelligence
                                 │
                                 ├── Models/
                                 │   ├── oip-startup-sentiment-v1
                                 │   ├── oip-startup-ner-v1
                                 │   ├── oip-startup-failure-predictor-v1
                                 │   └── oip-startup-embedding-v1
                                 │
                                 ├── Datasets/
                                 │   ├── startup-news-sentiment
                                 │   ├── startup-ner-annotated
                                 │   └── startup-failure-dataset
                                 │
                                 └── Spaces/
                                     ├── startup-sentiment-demo
                                     ├── startup-ner-demo
                                     └── startup-risk-calculator
```

### 3.2 Model Cards (Per Model)

Each model gets a comprehensive `README.md` (Model Card) with:

```markdown
# oip-startup-sentiment-v1

## Model Description
Fine-tuned DistilBERT for startup news sentiment analysis.
Classifies news about startups as positive, negative, or neutral.

## Intended Use
- Analyze sentiment of startup news articles
- Track startup ecosystem health
- Power startup risk scoring dashboards

## Training Data
5,247 startup news articles from TechCrunch, Hacker News,
SEC filings, and funding announcements.

## Performance
| Metric    | Score |
|-----------|-------|
| Accuracy  | 0.87  |
| F1 (macro)| 0.85  |
| Precision | 0.86  |
| Recall    | 0.84  |

## Quick Start
from transformers import pipeline
classifier = pipeline("text-classification",
    model="oip-startup-intelligence/oip-startup-sentiment-v1")
result = classifier("Stripe raises $6.5B at $50B valuation")
# → [{"label": "positive", "score": 0.94}]

## Limitations
- English only
- Trained on 2020-2024 news (may not generalize to older texts)
- Startup-specific; may underperform on general news
```

### 3.3 Demo Spaces (Gradio Apps)

**Space 1: Startup Sentiment Analyzer**
```
Input:  Text box for news article/paste URL
Output: Sentiment label + confidence bar + word highlighting
```

**Space 2: Startup NER Extractor**
```
Input:  Text box for startup-related text
Output: Highlighted entities (color-coded by type)
        + Table of extracted entities
```

**Space 3: Startup Risk Calculator**
```
Input:  Form fields (sector, funding, country, year founded)
Output: Risk score gauge (0-100) + risk level + recommendation
```

---

## Phase 4: Integration Back into Project (Week 4)

### 4.1 Update Existing Components

```
agents/
├── model_manager_agent.py     # Add HF model loading
├── sentiment_agent.py         # Option to use oip-startup-sentiment-v1
└── ml_predictor_agent.py      # Use oip-startup-failure-predictor-v1

nlp/
├── ner_pipeline.py            # Option to use oip-startup-ner-v1
├── embedding_generator.py     # Option to use oip-startup-embedding-v1
└── text_classifier.py         # Option to use HF sentiment model
```

### 4.2 Config Updates (`config/settings.yaml`)

```yaml
nlp:
  sentiment:
    provider: "huggingface"          # "vader" | "ollama" | "huggingface"
    model: "oip-startup-intelligence/oip-startup-sentiment-v1"
    fallback: "vader"

  ner:
    provider: "huggingface"          # "spacy" | "huggingface"
    model: "oip-startup-intelligence/oip-startup-ner-v1"
    fallback: "spacy"

  embedding:
    provider: "huggingface"
    model: "oip-startup-intelligence/oip-startup-embedding-v1"
    fallback: "all-MiniLM-L6-v2"

  failure_prediction:
    provider: "huggingface"          # "sklearn" | "huggingface"
    model: "oip-startup-intelligence/oip-startup-failure-predictor-v1"
    fallback: "sklearn"
```

---

## Timeline & Effort

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WEEK    TASK                              HOURS   DEPENDENCY        │
│  ────    ────                              ─────   ──────────        │
│                                                                      │
│  Week 1  Data Preparation                                        │
│         1.1 Extract & label sentiment data      8h     DB access    │
│         1.2 Annotate NER data (BIO format)      10h    spaCy assist │
│         1.3 Prepare failure prediction dataset  4h     DB + Kaggle  │
│         1.4 Create dataset scripts              4h                  │
│                                              ─────                   │
│                                              26h                    │
│                                                                      │
│  Week 2  Model Training                                           │
│         2.1 Train startup-sentiment-v1          8h    GPU optional  │
│         2.2 Train startup-ner-v1                10h   GPU optional  │
│         2.3 Export failure predictor to HF       4h                  │
│         2.4 Evaluate & benchmark all models     6h                  │
│                                              ─────                   │
│                                              28h                    │
│                                                                      │
│  Week 3  HF Hub Publication + Demos                               │
│         3.1 Create HF organization              2h                  │
│         3.2 Write model cards + README          6h                  │
│         3.3 Publish models to HF Hub            4h                  │
│         3.4 Publish datasets                    3h                  │
│         3.5 Build Gradio demo spaces            12h                 │
│                                              ─────                   │
│                                              27h                    │
│                                                                      │
│  Week 4  Integration + Testing                                    │
│         4.1 Add HF provider to model_manager    6h                  │
│         4.2 Update NLP pipelines with fallback  6h                  │
│         4.3 Add config for model switching      3h                  │
│         4.4 Integration tests                   4h                  │
│         4.5 Documentation + blog post draft     3h                  │
│                                              ─────                   │
│                                              22h                    │
│  ─────────────────────────────────────────────                     │
│  TOTAL                                       ~103h                  │
│  CALENDAR                                   4 weeks                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Competitive Positioning

### Current HF Landscape (From Our Research)

| Existing Model | Downloads | Gap |
|---------------|-----------|-----|
| `FinancialBERT-Sentiment` | 213K | Generic finance, not startup-specific |
| `distilroberta-financial-sentiment` | 212K | Same as above |
| `bert-base-NER` (dslim) | 1M+ | General NER, no STARTUP/FUNDING/TECHNOLOGY entities |
| `Startup-Exchange/tps_sentimental_analysis` | 15 | Tiny, not production-quality |

### Our Differentiation

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  OTHERS:                    US:                                  │
│  ───────                    ──                                   │
│  Generic finance NLP    →  Startup-specific NLP                  │
│  General sentiment      →  Startup failure/success signals       │
│  General NER            →  STARTUP/TECHNOLOGY/MARKET entities    │
│  Standalone models      →  Full pipeline + 30 collectors         │
│  No domain data         →  Curated startup datasets              │
│                                                                  │
│  RESULT: We become the "go-to" for startup ML.                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

| Metric | Target (3 months) | Target (6 months) |
|--------|-------------------|-------------------|
| Model downloads (total) | 5,000 | 50,000 |
| HF org followers | 200 | 1,000 |
| Academic citations | 2-3 | 10+ |
| Demo Space visitors | 1,000/month | 5,000/month |
| Community contributions | PRs to dataset | Fine-tuned variants |
| Inbound leads (from HF) | 10 | 50 |

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Insufficient labeled data | Medium | High | Use LLM-assisted labeling + Kaggle datasets |
| Poor model performance | Low | Medium | Rule-based fallback already works well |
| HF account/branding issues | Low | Low | Create org account early (Week 3) |
| GPU costs for training | Medium | Low | DistilBERT trains on CPU in ~2h |
| Community non-adoption | Medium | Medium | Publish dataset first, build community |
| Competitor publishes first | Low | High | Fast execution — 4-week timeline |

---

## File Structure (New Files to Create)

```
Startup_Research_Report/
├── scripts/
│   └── train_hf_models/
│       ├── __init__.py
│       ├── train_sentiment.py           # Fine-tune DistilBERT sentiment
│       ├── train_ner.py                 # Fine-tune BERT NER
│       ├── train_failure.py             # Export sklearn → HF
│       ├── train_embedding.py           # Fine-tune sentence-transformer
│       ├── prepare_datasets.py          # Extract + label data from DB
│       ├── annotate_ner.py              # Auto-annotate NER data
│       ├── publish_to_hub.py            # Push models to HF Hub
│       ├── benchmark.py                 # Compare with existing HF models
│       └── common/
│           ├── __init__.py
│           ├── data_loader.py
│           └── metrics.py
│
├── data/
│   └── hf_datasets/                     # Training datasets (gitignored)
│       ├── startup_sentiment/
│       ├── startup_ner/
│       └── startup_failure/
│
├── hf_spaces/
│   ├── sentiment_demo/
│   │   ├── app.py                       # Gradio sentiment demo
│   │   └── requirements.txt
│   ├── ner_demo/
│   │   ├── app.py                       # Gradio NER demo
│   │   └── requirements.txt
│   └── risk_calculator/
│       ├── app.py                       # Gradio risk calculator
│       └── requirements.txt
│
└── docs/
    └── engineering/
        └── HUGGINGFACE_PUBLICATION_PLAN.md  ← This file
```

---

## Next Steps (Immediate Actions)

- [ ] **Action 1:** Create Hugging Face organization account (`oip-startup-intelligence`)
- [ ] **Action 2:** Run `prepare_datasets.py` to extract training data from DB
- [ ] **Action 3:** Install training dependencies: `pip install transformers datasets accelerate`
- [ ] **Action 4:** Start with easiest model — `startup-sentiment-v1` (DistilBERT fine-tune)
- [ ] **Action 5:** Benchmark against `FinancialBERT-Sentiment` to validate improvement

---

*This plan aligns with the GTM Strategy (KILLER MOVE 4: Open Model Weights) and
positions OIP as the canonical source for startup intelligence ML models.*
