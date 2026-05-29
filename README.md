# Clinical Research Pipeline (CRP)

> A full-lifecycle clinical research assistant: from background mining → literature integration → study design → statistical planning → auto PPT generation, with a 5-phase interactive guided workflow and bilingual (Chinese/English) output.

> 医学临床实验全生命周期助手：从研究背景挖掘 → 文献整合 → 实验设计 → 统计分析 → PPT 生成，5 阶段交互式引导，中英双语。

## Architecture

```
Input: Research Topic
      │
      ▼
┌─────────────────────────────────────────┐
│          5-Phase Interactive Pipeline    │
├─────────────────────────────────────────┤
│ Phase 1: Background & Story Mining       │
│ Phase 2: Literature Integration          │
│ Phase 3: Study Design Planning           │
│ Phase 4: Statistics + Limitations        │
│ Phase 5: Auto PPT Generation             │
└─────────────────────────────────────────┘
      │
      ▼
Output: Complete Research Proposal PPT + Structured Docs
```

## Quick Start

### Prerequisites

```bash
pip install python-pptx jieba
```

### Usage (Claude Code)

```
/clinical-research
```

Then follow the interactive prompts — input your research topic, select language (`zh`/`en`), and choose output type (Research Proposal / Final Report / Grant Application).

### Trigger Keywords

The skill auto-activates on: 临床研究, 临床实验, 开题报告, 课题设计, CRP, 研究方案, 文献综述, clinical trial, study design, PICO

### Standalone Scripts

```bash
# PubMed search
python scripts/pubmed_search.py search "SGLT2 inhibitor heart failure" --max 20

# PICO-structured search
python scripts/pubmed_search.py pico "heart failure" "SGLT2 inhibitor" "standard care" "mortality"

# Keyword extraction
python scripts/keyword_extract.py --input search_results.json --output analysis.json

# Sample size calculation
python scripts/sample_size.py means --m1 120 --m2 110 --sd 20
python scripts/sample_size.py proportions --p1 0.30 --p2 0.20
python scripts/sample_size.py survival --hr 0.70 --event-rate 0.30

# PPT generation
python scripts/ppt_builder.py \
  --input-dir ./crp_output \
  --output final_report.pptx \
  --lang zh \
  --type 开题报告
```

## File Structure

```
├── SKILL.md                          # Main entry point & 5-phase orchestrator
├── references/
│   ├── phase1-background.md          # Background mining (PubMed + CNKI + CT.gov)
│   ├── phase2-literature.md          # Literature integration & keyword analysis
│   ├── phase3-design.md             # Study design (PICO, sample size, flowchart)
│   ├── phase4-statistics.md         # Statistical plan + limitations catalog
│   └── phase5-ppt.md               # Auto PPT generation
├── templates/
│   ├── lit_matrix.md / _en.md       # PICOS literature matrix (zh/en)
│   ├── design_checklist.md / _en.md # CONSORT/STROBE checklist (zh/en)
│   └── limitations_catalog.md / _en.md # Limitations catalog (zh/en)
├── scripts/
│   ├── pubmed_search.py             # PubMed E-utilities API (zero-dependency)
│   ├── keyword_extract.py           # Keyword extraction + co-occurrence + clustering
│   ├── sample_size.py               # Sample size: means/proportions/survival/equivalence
│   └── ppt_builder.py              # PPT builder (python-pptx, 16:9, bilingual)
└── data/
    └── project_state.json           # Resumable project state
```

## Features

- 🌐 **Bilingual**: Full Chinese (`zh`) and English (`en`) output support
- 🔍 **PubMed Integration**: E-utilities API — no API key required
- 📊 **Keyword Analysis**: TF-IDF + co-occurrence networks + theme clustering
- 📐 **Sample Size**: Means, proportions, survival analysis, equivalence/non-inferiority
- 📑 **Auto PPT**: 10-14 slide decks with professional dark-blue theme
- 💾 **Resumable**: State saved after each phase — pick up where you left off
- 🏥 **Guideline-Compliant**: CONSORT, STROBE, PRISMA, STARD checklists built-in

## License

MIT
