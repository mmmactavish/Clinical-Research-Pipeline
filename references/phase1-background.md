# Phase 1: 研究故事背景挖掘

## 目标

帮学生回答三个问题：
1. **这个研究领域发生了什么？** → 研究现状全景
2. **还缺什么？** → 知识空白
3. **为什么现在做这个？** → 研究的时机和意义

---

## 执行步骤

### Step 1: 解析用户输入

从用户输入中提取：
- 核心概念（疾病、干预、人群、结局方向）
- 中英文关键词各一组
- 如果用户输入太宽泛（如"心脏病"），先追问细化到「疾病-干预-结局」三个要素

### Step 2: 并行文献检索

同时启动三个搜索方向：

**A. PubMed 高影响力综述**
```
python scripts/pubmed_search.py search "<英文关键词> review" --max 10 --year-start <当前年-5>
```
关注：领域共识、指南推荐、未满足需求

**B. PubMed 重要 RCT / 观察性研究**
```
python scripts/pubmed_search.py search "<英文关键词>" --max 10 --year-start <当前年-5>
```
关注：里程碑式研究、大型多中心研究

**C. 中文文献 + 指南**
使用 WebSearch：搜索词为 `<中文关键词> 指南 OR meta OR 系统综述 site:cnki.net`
使用 WebSearch：搜索词为 `<中文关键词> 临床研究 site:wanfangdata.com.cn`

**D. ClinicalTrials.gov**
使用 WebSearch：`site:clinicaltrials.gov <英文关键词>` — 了解正在进行的竞争

### Step 3: 综合分析

从搜索结果中提炼：

1. **PICO 框架**（初版，后续阶段会精化）：
   - P (Population): 现有研究主要关注哪类人群？
   - I (Intervention): 主流干预/暴露是什么？
   - C (Comparison): 常用对照是什么？
   - O (Outcome): 常用终点是什么？

2. **知识空白矩阵**：
   | 已知 (What's Known) | 未知 (What's Unknown) | 为什么重要 (Why It Matters) |
   |---------------------|------------------------|-----------------------------|
   | ...                 | ...                    | ...                         |

3. **研究故事线**：
   用一段话（500-800字）描述：
   - 疾病负担 → 现有治疗局限 → 新方法的理论基础 → 需要回答的关键问题
   - 这段是开题报告/论文 Introduction 的核心骨架

### Step 4: 输出文件

写入 `<output_dir>/phase1_background/`：

- `01_background.md` — 结构化背景（包含 PICO 草稿 + 文献检索策略）
- `02_knowledge_gap.md` — 知识空白矩阵
- `03_storyline.md` — 叙事版研究动机
- `search_results.json` — 原始检索结果缓存（供后续阶段使用）

### Step 5: 用户确认

展示给用户：
1. 提取的 PICO 框架（用中文简述）
2. 知识空白矩阵中最关键的 2-3 个空白
3. 故事线摘要（3-5 句话）

**确认话术**：
> 这是我从文献中提取的初步分析。PICO 框架和知识空白是否符合你的理解？有没有需要调整的地方？确认后我们进入文献深度整合。

---

## 注意事项

- ✅ 如果 PubMed 返回结果 < 5 条，放宽检索条件（去掉年份限制或 article type 过滤）
- ✅ 所有文献引用都必须来自实际搜索结果，不要编造
- ✅ 如果用户的研究是观察性设计（非 RCT），在 PICO 框架中标注"O"为 Outcome（非 Intervention）
- ✅ 中英文搜索结果有差异很正常，在报告中注明"中文文献补充了XX视角"
- ❌ 不要在这一阶段给出研究设计建议 — 那是 Phase 3 的工作
- ❌ 不要在这一阶段做详细的文献质量评估 — 那是 Phase 2 的工作
