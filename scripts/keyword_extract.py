"""
关键词提取 + 共现分析
支持中英文混合文本，输出 JSON 格式的关键词分析报告

用法:
    python keyword_extract.py --input search_results.json --output keyword_analysis.json
    python keyword_extract.py --text "abstract text here..." --lang en

依赖: pip install jieba nltk
"""

import json
import sys
import argparse
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Optional


# === 停用词（中英文） ===
EN_STOP_WORDS = {
    "the", "a", "an", "of", "in", "to", "for", "with", "on", "at", "from",
    "by", "about", "as", "into", "through", "during", "before", "after",
    "above", "below", "between", "and", "or", "but", "not", "than", "this",
    "that", "these", "those", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "its", "his", "her",
    "their", "our", "your", "my", "we", "they", "he", "she", "it", "all",
    "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "only", "same", "so", "up", "out", "if", "then", "also", "very",
    "just", "now", "here", "there", "when", "where", "why", "how", "which",
    "who", "whom", "what", "was", "were", "been", "had", "study", "patients",
    "results", "conclusion", "background", "methods", "aim", "objective",
    "purpose", "significant", "associated", "analysis", "data", "using",
    "among", "including", "without", "well", "however", "therefore",
    "although", "whereas", "furthermore", "additional", "clinical", "trial",
    "randomized", "controlled", "outcomes", "compared", "versus", "vs",
}

CN_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "所", "为", "所以", "因为", "但是", "然而", "而且", "可以", "这个",
    "那个", "什么", "怎么", "如何", "哪", "吗", "啊", "呢", "吧", "被",
    "把", "从", "对", "与", "或", "及", "之", "中", "等", "其", "将",
    "研究", "患者", "结果", "结论", "方法", "背景", "目的", "分析",
    "进行", "采用", "发现", "显示", "表明", "提示", "具有", "意义",
    "统计学", "显著", "差异", "相关", "比较", "两组", "对照组",
    "实验组", "观察组", "治疗组", "纳入", "排除", "随机", "对照",
    "临床试验", "分别", "平均", "包括", "使用", "通过", "不同",
    "所有", "明显", "明显", "之间", "无", "一种", "主要", "重要",
    "可能", "目前", "需要", "一种", "其中", "增加", "减少", "提高",
    "降低", "改善", "影响", "作用", "水平", "时间", "情况",
}


def _load_jieba():
    """延迟加载 jieba"""
    try:
        import jieba
        return jieba
    except ImportError:
        sys.stderr.write("Error: jieba not installed. Run: pip install jieba\n")
        sys.exit(1)


def extract_keywords_en(text: str, top_n: int = 50) -> list[tuple[str, int, float]]:
    """英文关键词提取 (TF-IDF 简化版: TF × IDF approximation)"""
    # Tokenize
    words = re.findall(r'\b[a-zA-Z][a-zA-Z\-]{2,}\b', text.lower())
    # 去停用词
    filtered = [w for w in words if w not in EN_STOP_WORDS]

    # Term frequency
    tf = Counter(filtered)
    total_terms = sum(tf.values())

    # 简单的 TF-IDF (since we process a single document set, use log-normalized TF)
    results = []
    for term, count in tf.most_common(top_n * 2):
        if len(term) <= 2:
            continue
        tf_norm = count / total_terms if total_terms > 0 else 0
        # Simple scoring: log-scaled TF (since we can't compute true IDF on one doc set)
        score = count * (1 + __import__('math').log(total_terms / count)) if count > 0 else 0
        results.append((term, count, round(score, 4)))

    # Sort by score
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_n]


def extract_keywords_cn(text: str, top_n: int = 50) -> list[tuple[str, int, float]]:
    """中文关键词提取 (基于 jieba TF-IDF)"""
    jieba = _load_jieba()

    # 分词
    words = jieba.cut(text)
    filtered = [w for w in words if len(w) >= 2 and w not in CN_STOP_WORDS]

    # Term frequency
    tf = Counter(filtered)
    total_terms = sum(tf.values())

    import math
    results = []
    for term, count in tf.most_common(top_n * 2):
        if len(term) < 2:
            continue
        score = count * (1 + math.log(total_terms / count)) if count > 0 else 0
        results.append((term, count, round(score, 4)))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_n]


def build_cooccurrence(
    keywords_en: list[str],
    keywords_cn: list[str],
    documents: list[str],
    window_size: int = 20,
) -> dict:
    """
    构建关键词共现矩阵（简化版：基于同一文档中的共同出现）
    """
    cooc = defaultdict(lambda: defaultdict(int))
    all_keywords = set(keywords_en + keywords_cn)

    for doc in documents:
        doc_lower = doc.lower()
        present = [kw for kw in all_keywords if kw.lower() in doc_lower]
        for a, b in combinations(sorted(present), 2):
            cooc[a][b] += 1
            cooc[b][a] += 1

    # 提取 top edges
    edges = []
    seen = set()
    for kw1 in cooc:
        for kw2 in cooc[kw1]:
            pair = tuple(sorted([kw1, kw2]))
            if pair in seen:
                continue
            seen.add(pair)
            if cooc[kw1][kw2] >= 2:  # 最少共现 2 次
                edges.append({
                    "source": pair[0],
                    "target": pair[1],
                    "weight": cooc[kw1][kw2],
                })

    edges.sort(key=lambda e: e["weight"], reverse=True)
    return {
        "edges": edges[:50],  # top 50 edges
        "total_cooccurrences": len(edges),
    }


def cluster_keywords(keywords: list[tuple[str, int, float]], cooc: dict) -> list[dict]:
    """
    简单的关键词聚类：基于共现关系的贪心聚类
    将高频关键词分组为主题簇
    """
    top_kw = [kw for kw, _, _ in keywords[:30]]
    assigned = set()
    clusters = []

    # 构建邻接表
    adj = defaultdict(set)
    for edge in cooc.get("edges", []):
        adj[edge["source"]].add(edge["target"])
        adj[edge["target"]].add(edge["source"])

    for kw in top_kw:
        if kw in assigned:
            continue
        # BFS 收集相关词
        cluster = {kw}
        queue = [kw]
        while queue:
            current = queue.pop(0)
            for neighbor in adj.get(current, set()):
                if neighbor not in cluster and neighbor in set(top_kw):
                    if len(cluster) < 8:  # 每个簇最多 8 个词
                        cluster.add(neighbor)
                        queue.append(neighbor)

        assigned.update(cluster)
        if len(cluster) >= 2:
            clusters.append({
                "theme": kw if kw in ["the", "a"] else list(cluster)[0],  # 用第一个词作主题名
                "keywords": sorted(cluster),
                "size": len(cluster),
            })

    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters[:8]


def analyze_trend(pmids_by_year: dict[str, list[str]], keywords: list[str]) -> list[dict]:
    """
    时间趋势分析：统计每个关键词在各年份的出现频率

    Args:
        pmids_by_year: {year: [pmid, ...]}
        keywords: top keywords to track
    """
    trends = []
    years = sorted(pmids_by_year.keys())

    for kw in keywords[:10]:
        yearly_counts = {}
        for year in years:
            yearly_counts[year] = 0  # Simplified: would need per-year abstracts
        trends.append({
            "keyword": kw,
            "yearly_data": yearly_counts,
            "trend": "stable",  # "rising", "stable", "declining"
        })

    return trends


def load_pubmed_results(filepath: str) -> list[dict]:
    """加载 PubMed 搜索结果 JSON"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def main():
    parser = argparse.ArgumentParser(description="Keyword Extraction for CRP")
    parser.add_argument("--input", help="Path to PubMed search results JSON")
    parser.add_argument("--text", help="Direct text input (overrides --input)")
    parser.add_argument("--lang", default="mixed", choices=["en", "cn", "mixed"],
                       help="Language of input text")
    parser.add_argument("--output", default="keyword_analysis.json",
                       help="Output JSON file path")
    parser.add_argument("--top-n", type=int, default=30, help="Top N keywords")
    args = parser.parse_args()

    # 收集文本
    if args.text:
        all_text = args.text
    elif args.input:
        papers = load_pubmed_results(args.input)
        all_text = " ".join(
            f"{p.get('title', '')} {p.get('abstract', '')}"
            for p in papers
        )
    else:
        sys.stderr.write("Error: Either --input or --text required\n")
        sys.exit(1)

    # 分离中英文
    # Simple heuristic: 中文字符占比 > 30% → Chinese segment
    cn_chars = len(re.findall(r'[一-鿿]', all_text))
    en_chars = len(re.findall(r'[a-zA-Z]', all_text))

    results = {}

    # 英文关键词
    if args.lang in ("en", "mixed") and en_chars > 50:
        en_keywords = extract_keywords_en(all_text, args.top_n)
        results["en_keywords"] = [
            {"keyword": kw, "count": c, "score": s} for kw, c, s in en_keywords
        ]
        sys.stderr.write(f"Extracted {len(en_keywords)} English keywords\n")

        # 人工标注主题标签（基于高频词推断）
        top_en = [kw for kw, _, _ in en_keywords[:5]]
        results["en_themes"] = _infer_themes(top_en)

    # 中文关键词
    if args.lang in ("cn", "mixed") and cn_chars > 20:
        cn_keywords = extract_keywords_cn(all_text, args.top_n)
        results["cn_keywords"] = [
            {"keyword": kw, "count": c, "score": s} for kw, c, s in cn_keywords
        ]
        sys.stderr.write(f"Extracted {len(cn_keywords)} Chinese keywords\n")

    # 共现分析
    en_kw_list = [kw for kw, _, _ in results.get("en_keywords", [])]
    cn_kw_list = [kw for kw, _, _ in results.get("cn_keywords", [])]
    documents = [all_text]  # single corpus
    if args.input:
        papers = load_pubmed_results(args.input)
        documents = [f"{p.get('title','')} {p.get('abstract','')}" for p in papers]

    cooc = build_cooccurrence(en_kw_list, cn_kw_list, documents)
    results["cooccurrence"] = cooc

    # 聚类
    all_keywords = (results.get("en_keywords", []) + results.get("cn_keywords", []))
    clusters = cluster_keywords(all_keywords, cooc)
    results["clusters"] = clusters
    sys.stderr.write(f"Found {len(clusters)} keyword clusters\n")

    # 趋势 - simplified
    results["trends"] = {"note": "Trend analysis requires per-year abstract data. Run with year-segmented input for detailed trends."}

    # 输出
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(json.dumps({"status": "ok", "output": args.output,
                      "en_keywords": len(results.get("en_keywords", [])),
                      "cn_keywords": len(results.get("cn_keywords", [])),
                      "clusters": len(clusters)}))


def _infer_themes(keywords: list[str]) -> list[str]:
    """从高频英文关键词推断研究主题"""
    theme_patterns = {
        "cardiovascular": ["heart", "cardiac", "cardiovascular", "myocardial", "hf", "heart failure", "mi", "infarction"],
        "metabolic": ["diabetes", "glucose", "insulin", "metabolic", "obesity", "lipid"],
        "renal": ["kidney", "renal", "ckd", "egfr", "nephro", "dialysis"],
        "neurological": ["brain", "stroke", "neurological", "cognitive", "dementia", "alzheimer"],
        "oncology": ["cancer", "tumor", "survival", "chemotherapy", "malignancy"],
        "respiratory": ["lung", "copd", "asthma", "respiratory", "pulmonary"],
        "inflammation": ["inflammation", "inflammatory", "cytokine", "immune"],
        "mortality": ["mortality", "death", "survival", "prognosis"],
        "biomarker": ["biomarker", "marker", "nt-probnp", "troponin", "crp", "predictor"],
        "intervention": ["trial", "intervention", "efficacy", "safety", "treatment"],
    }

    matched = []
    for theme, patterns in theme_patterns.items():
        score = sum(1 for p in patterns if any(p in kw.lower() for kw in keywords))
        if score >= 2:
            matched.append(theme)

    return matched[:5] if matched else ["general medicine"]


if __name__ == "__main__":
    main()
