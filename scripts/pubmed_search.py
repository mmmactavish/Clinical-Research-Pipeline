"""
PubMed E-utilities API 封装
NCBI Entrez Programming Utilities — 公开免费，无需 API Key
文档: https://www.ncbi.nlm.nih.gov/books/NBK25501/

用法:
    python pubmed_search.py search "SGLT2 inhibitor heart failure" --max 20
    python pubmed_search.py fetch "12345678,23456789" --format abstract
    python pubmed_search.py pico "heart failure" "SGLT2 inhibitor" "standard care" "cardiovascular death"

输出: JSON 到 stdout，日志到 stderr
"""

import json
import sys
import argparse
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional

# === Config ===
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "crp_clinical_research"
EMAIL = "crp@example.com"  # NCBI 要求标识调用者
REQUEST_DELAY = 0.34  # NCBI 限制: 3 req/s (无 API key), 10 req/s (有 API key)


def _make_request(url: str, max_retries: int = 3) -> str:
    """发送 HTTP 请求，带重试和速率控制"""
    time.sleep(REQUEST_DELAY)
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt
                sys.stderr.write(f"Rate limited, retrying in {wait}s...\n")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
    raise RuntimeError(f"Failed after {max_retries} retries: {url}")


def search(query: str, max_results: int = 20, year_start: int = None,
           article_type: str = None) -> list[dict]:
    """
    搜索 PubMed

    Args:
        query: 搜索词（支持 PubMed 查询语法）
        max_results: 最大返回数
        year_start: 起始年份（如 2020）
        article_type: 文章类型过滤（如 "Randomized Controlled Trial", "Review", "Meta-Analysis"）

    Returns:
        [{pmid, title, year, journal, authors, doi}, ...]
    """
    # 构建查询
    search_terms = [query]
    if year_start:
        search_terms.append(f'("{year_start}"[Date - Publication] : "3000"[Date - Publication])')
    if article_type:
        search_terms.append(f'"{article_type}"[Publication Type]')

    full_query = " AND ".join(search_terms)

    # ESearch
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": full_query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
        "tool": TOOL,
        "email": EMAIL,
    })
    url = f"{BASE_URL}/esearch.fcgi?{params}"
    data = json.loads(_make_request(url))

    id_list = data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    # EFetch (获取摘要等详细信息)
    return _fetch_details(id_list)


def _fetch_details(pmids: list[str]) -> list[dict]:
    """获取文献详细信息"""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": TOOL,
        "email": EMAIL,
    })
    url = f"{BASE_URL}/efetch.fcgi?{params}"
    xml_data = _make_request(url)

    root = ET.fromstring(xml_data)
    results = []

    for article_elem in root.findall(".//PubmedArticle"):
        try:
            article = _parse_article(article_elem)
            results.append(article)
        except Exception as e:
            sys.stderr.write(f"Parse error for PMID: {e}\n")

    return results


def _parse_article(elem: ET.Element) -> dict:
    """解析单篇 XML → 结构化 dict"""
    medline = elem.find(".//MedlineCitation")
    article = medline.find(".//Article")

    pmid = medline.findtext(".//PMID", "")

    # 标题
    title = article.findtext(".//ArticleTitle", "")

    # 期刊
    journal = article.findtext(".//Journal/Title", "")

    # 年份
    year = article.findtext(".//Journal/JournalIssue/PubDate/Year", "")
    if not year:
        year = article.findtext(".//Journal/JournalIssue/PubDate/MedlineDate", "")[:4]

    # 作者 (前 5 位)
    authors = []
    for author_elem in article.findall(".//AuthorList/Author")[:5]:
        last = author_elem.findtext("LastName", "")
        fore = author_elem.findtext("ForeName", "")
        if last:
            authors.append(f"{last} {fore}")

    # 摘要
    abstract_parts = []
    for ab_elem in article.findall(".//Abstract/AbstractText"):
        label = ab_elem.get("Label", "")
        text = ab_elem.text or ""
        if label:
            abstract_parts.append(f"{label}: {text}")
        else:
            abstract_parts.append(text)
    abstract = " ".join(abstract_parts)

    # DOI
    doi = ""
    for eid in article.findall(".//ELocationID"):
        if eid.get("EIdType") == "doi":
            doi = eid.text or ""

    # 出版类型
    pub_types = [
        pt.text for pt in article.findall(".//PublicationTypeList/PublicationType") if pt.text
    ]

    # MeSH 词条
    mesh_terms = []
    for mesh in medline.findall(".//MeshHeadingList/MeshHeading"):
        descriptor = mesh.findtext("DescriptorName", "")
        if descriptor:
            mesh_terms.append(descriptor)

    return {
        "pmid": pmid,
        "title": title.strip(),
        "journal": journal.strip(),
        "year": year,
        "authors": authors,
        "doi": doi,
        "abstract": abstract.strip(),
        "publication_types": pub_types,
        "mesh_terms": mesh_terms,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }


def search_pico(
    population: str = "",
    intervention: str = "",
    comparison: str = "",
    outcome: str = "",
    study_design: Optional[str] = None,
    max_results: int = 20,
) -> list[dict]:
    """
    PICO 框架搜索 — 自动构建 PubMed 检索式

    将 PICO 要素组合为 PubMed 查询:
    (Population) AND (Intervention) AND (Outcome)
    """
    query_parts = []
    if population:
        query_parts.append(f"({population})")
    if intervention:
        query_parts.append(f"({intervention})")
    if outcome:
        query_parts.append(f"({outcome})")

    if not query_parts:
        raise ValueError("At least one PICO element required")

    query = " AND ".join(query_parts)

    # 可选 AND NOT comparison (如果要排除对照)
    # 通常 comparison 不加入检索式，而是用于筛选

    # 如果指定研究设计，添加过滤器
    article_type = None
    study_design_filters = {
        "rct": "Randomized Controlled Trial",
        "cohort": None,  # 观察性研究无固定 Publication Type
        "case-control": None,
        "cross-sectional": None,
        "systematic-review": "Meta-Analysis",
        "meta-analysis": "Meta-Analysis",
    }
    if study_design:
        article_type = study_design_filters.get(study_design.lower())

    return search(query, max_results=max_results, article_type=article_type)


def fetch_by_pmids(pmids: list[str]) -> list[dict]:
    """通过 PMID 列表获取详细信息"""
    return _fetch_details(pmids)


# === CLI ===
def main():
    parser = argparse.ArgumentParser(description="PubMed Search CLI for CRP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search 子命令
    sp = subparsers.add_parser("search", help="Search PubMed")
    sp.add_argument("query", help="Search query")
    sp.add_argument("--max", type=int, default=20, help="Max results")
    sp.add_argument("--year-start", type=int, help="Start year")
    sp.add_argument("--type", dest="article_type", help="Article type filter")

    # fetch 子命令
    fp = subparsers.add_parser("fetch", help="Fetch by PMIDs")
    fp.add_argument("pmids", help="Comma-separated PMIDs")

    # pico 子命令
    pp = subparsers.add_parser("pico", help="PICO search")
    pp.add_argument("population")
    pp.add_argument("intervention")
    pp.add_argument("comparison")
    pp.add_argument("outcome")
    pp.add_argument("--design", dest="study_design", default=None)
    pp.add_argument("--max", type=int, default=20)

    args = parser.parse_args()

    try:
        if args.command == "search":
            results = search(args.query, args.max, args.year_start, args.article_type)
        elif args.command == "fetch":
            pmids = [p.strip() for p in args.pmids.split(",") if p.strip()]
            results = fetch_by_pmids(pmids)
        elif args.command == "pico":
            results = search_pico(
                population=args.population,
                intervention=args.intervention,
                comparison=args.comparison,
                outcome=args.outcome,
                study_design=args.study_design,
                max_results=args.max,
            )

        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.stderr.write(f"Found {len(results)} results\n")

    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
