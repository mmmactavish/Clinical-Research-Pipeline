# Phase 5: PPT 自动生成

## 目标

将 Phase 1-4 的所有结构化输出，整合为一份可直接用于汇报的 PPT。

---

## 执行步骤

### Step 1: 收集输入

读取前 4 个 Phase 的所有输出文件：
```
phase1_background/01_background.md
phase1_background/02_knowledge_gap.md
phase1_background/03_storyline.md
phase2_literature/04_literature_matrix.md
phase2_literature/05_keyword_analysis.md
phase2_literature/06_inspiration.md
phase3_design/07_study_design.md
phase3_design/09_reference_cases.md
phase4_statistics/10_statistical_plan.md
phase4_statistics/11_limitations.md
phase4_statistics/12_future_directions.md
```

### Step 2: 确定 Slide 结构

根据用户的目标用途自动调整 slide 结构：

#### 开题报告版（默认，10-14 slides）

```
1.  封面（标题 + 作者信息）
2.  目录
3.  研究背景 — 疾病负担与未满足需求
4.  研究背景 — 现有证据与知识空白
5.  文献综述 — 关键文献矩阵
6.  文献综述 — 关键词热点与趋势
7.  研究目的与假设
8.  研究设计 — 类型 + PICO
9.  研究设计 — 入排标准 + 流程图
10. 样本量估算
11. 统计分析计划
12. 预期结果（模拟表格/图形）
13. 不足与展望
14. 致谢 / Q&A
```

#### 结题汇报版（10-14 slides）

```
1.  封面（标题 + 作者信息）
2.  目录
3.  研究背景与目的（精简版）
4.  研究设计与方法
5.  基线特征
6.  主要结果
7.  次要结果
8.  亚组分析
9.  安全性（如 RCT）
10. 讨论 — 与既往研究对比
11. 不足与展望
12. 结论
13. 致谢 / Q&A
```

#### 基金申请版（8-10 slides）

```
1.  封面
2.  立项依据（背景 + 知识空白）
3.  研究目标与假说
4.  研究方案概览
5.  关键技术路线
6.  可行性分析
7.  预期成果
8.  研究团队与预算
```

### Step 3: 内容映射与精简

对每个 slide，从源文件中提取关键内容并精简为口语化 bullet points：

**精简原则**：
- 每个 slide 不超过 6 个 bullet points
- 每个 bullet 不超过 2 行
- 数字 > 文字（能用数字表达的不用长句）
- 表格/流程图优先于纯文字

**内容映射表**：见 `scripts/ppt_builder.py` 中的 `SLIDE_CONTENT_MAP`

### Step 4: 生成 PPT

使用 python-pptx 生成：

```bash
python scripts/ppt_builder.py \
  --output <output_dir>/phase5_ppt/final_report.pptx \
  --title "<研究标题>" \
  --author "<作者信息>" \
  --type <开题报告|结题汇报|基金申请> \
  --input-dir <output_dir>
```

`ppt_builder.py` 会：
1. 读取所有 phase 输出文件
2. 按 slide 结构提取并精简内容
3. 使用统一模板渲染（配色、字体、布局）
4. 生成 `.pptx` 文件

### Step 5: 输出文件

写入 `<output_dir>/phase5_ppt/`：
- `final_report.pptx` — 最终 PPT
- `slide_content.json` — 每个 slide 的内容摘要（方便手动调整）

### Step 6: 用户确认

展示：
1. PPT 文件路径
2. Slide 结构概览（目录）
3. "你可以直接打开 `final_report.pptx` 进行最后的微调"

**确认话术**：
> PPT 已生成，共 [N] 页。文件在 `[路径]`。建议你检查一下数据准确性和排版细节。还需要我调整什么吗？

---

## PPT 样式规范

- **配色方案**：深蓝主色 (#1B3A5C) + 白色文字；强调色橙色 (#E87722)
- **中文字体**：微软雅黑（标题）、宋体（正文）
- **英文字体**：Calibri / Arial
- **图表**：柱状图、森林图、流程图优先用 python-pptx 的原生 shape 绘制
- **引用格式**：Vancouver 风格（[1], [2], ...）

---

## 注意事项

- ✅ 生成 PPT 前，确认所有 4 个 Phase 的输出文件都存在
- ✅ 如果某阶段缺失，提示用户先完成该阶段
- ✅ PPT 是"90% 成品" — 学生仍需检查数据和微调排版
- ✅ 字号不要太小（正文 ≥ 18pt），确保投影效果
- ❌ 不要试图在 PPT 中塞入所有细节 — PPT 是演讲辅助，细节在 markdown 文件里
