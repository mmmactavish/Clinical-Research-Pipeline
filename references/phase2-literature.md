# Phase 2: 文献整合与关键词提炼

## 目标

在 Phase 1 的基础上：
1. **系统性检索** → 更完整的文献覆盖
2. **结构化整理** → PICOS 文献矩阵
3. **关键词分析** → 研究热点 & 趋势
4. **启发式总结** → 给你的研究有什么启发？

---

## 执行步骤

### Step 1: 构建系统检索式

基于 Phase 1 确认的 PICO 框架，构建正式的 PubMed 检索式：

1. 识别 MeSH terms（通过搜索已知文献的 MeSH 标注）
2. 构建检索式模板：
   ```
   (Population terms[MeSH] OR Population terms[tiab]) AND
   (Intervention terms[MeSH] OR Intervention terms[tiab]) AND
   (Outcome terms[MeSH] OR Outcome terms[tiab])
   ```
3. 根据研究设计添加过滤：
   - RCT → `"Randomized Controlled Trial"[Publication Type]`
   - 系统综述 → `"Meta-Analysis"[Publication Type]` OR `"Systematic Review"[Publication Type]`
   - 观察性 → 不限定类型，但优先检索高质量的

4. 执行扩展检索：
   ```
   python scripts/pubmed_search.py search "<完整检索式>" --max 30
   ```

### Step 2: 知网/万方补充

使用 WebSearch 工具进行中文文献补充检索：
- 3-5 次有针对性的搜索（不同关键词组合）
- 重点关注：博硕士论文（了解国内研究生做了什么）、中文指南
- 如果 WebSearch 效果不好 → 提示用户手动导出 EndNote 格式

### Step 3: 文献筛选与 PICOS 矩阵

1. **去重**：PMID 去重 + 标题相似度去重
2. **初筛**：基于标题 + 摘要，排除明显不相关的
3. **PICOS 提取**：对每篇纳入文献，按 `templates/lit_matrix.md` 模板提取信息
4. **填充矩阵表格**

同时，如果要处理文献的全文摘要内容，运行关键词提取：
```
python scripts/keyword_extract.py --input search_results.json --output keyword_analysis.json
```

### Step 4: 关键词分析

1. **高频关键词 Top 20** （中英文分开统计）
2. **共现网络**：列出 5-8 组关键词聚类，每组命名一个主题标签
3. **时间趋势**：按年份观察关键词变化，标注"上升趋势 / 稳定 / 下降趋势"
4. **可视化建议**：用文字描述一个共现网络图的建议布局

### Step 5: 启发式总结

基于文献矩阵 + 关键词分析，撰写启发总结：

**A. 成功案例剖析**（3-5 个最相关的高质量研究）：
| 研究 | 设计亮点 | 可借鉴点 | 可改进点 |
|------|---------|---------|---------|
| ... |         |         |         |

**B. 方法学启示**：
- 主流研究设计是什么？（RCT 占X%，队列占Y%...）
- 最常用的主要终点是什么？
- 样本量中位数是多少？
- 有什么巧妙的方法学思路？（如使用工具变量、倾向评分匹配等）

**C. 你的研究可以定位于**：
- 这些研究没回答的问题
- 你可以在哪些方面做得更好（设计、人群、终点、随访）

### Step 6: 输出文件

写入 `<output_dir>/phase2_literature/`：
- `04_literature_matrix.md` — PICOS 文献矩阵表
- `05_keyword_analysis.md` — 关键词分析报告
- `06_inspiration.md` — 启发总结

### Step 7: 用户确认

展示：
1. 纳入文献数量（检索到X篇 → 去重后Y篇 → 纳入Z篇）
2. 最关键的成功案例（2-3 个）
3. 你的研究可以定位于什么空白

**确认话术**：
> 文献整合完成。共纳入 Z 篇高质量文献。你的研究最像这其中 [某篇] 的设计，但你可以在 [某方面] 做得更好。确认后我们进入实验设计阶段。

---

## 注意事项

- ✅ 如果文献太少（< 10 篇），可能检索式太窄 → 建议放宽
- ✅ 如果文献太多（> 50 篇），挑选最相关的 30 篇做深度分析
- ✅ 关键词分析的质量取决于摘要文本量 — 如果摘要不全，标注"需要全文"
- ✅ MeSH terms 是 PubMed 的核心优势，务必利用好
