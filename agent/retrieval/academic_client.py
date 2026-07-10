"""多源学术数据聚合客户端：OpenAlex / DBLP / arXiv / Crossref / Semantic Scholar"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from utils.path_tool import get_abs_path
from utils.logger_handler import logger

import httpx


@dataclass
class AcademicPaper:
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    citation_count: int = 0
    source: str = ""


class AcademicDataClient:
    CACHE_DIR = get_abs_path("data/cache")
    CACHE_TTL = 86400  # 24小时

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def _cache_key(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def _load_cache(self, query: str) -> list[AcademicPaper] | None:
        key = self._cache_key(query)
        cache_file = os.path.join(self.CACHE_DIR, f"{key}.json")
        if not os.path.exists(cache_file):
            return None
        if time.time() - os.path.getmtime(cache_file) > self.CACHE_TTL:
            os.remove(cache_file)
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [AcademicPaper(**item) for item in data]
        except Exception:
            return None

    def _save_cache(self, query: str, papers: list[AcademicPaper]):
        key = self._cache_key(query)
        cache_file = os.path.join(self.CACHE_DIR, f"{key}.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump([p.__dict__ for p in papers], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[AcademicClient]缓存写入失败: {e}")

    def search(self, query: str, max_results: int = 20) -> list[AcademicPaper]:
        # 先查缓存
        cached = self._load_cache(query)
        if cached is not None:
            logger.info(f"[AcademicClient]缓存命中: {query}")
            return cached

        all_papers: list[AcademicPaper] = []

        with httpx.Client(timeout=15.0) as client:
            # 并行请求多个源（顺序执行，共用 client）
            sources = [
                self._search_arxiv,
                self._search_crossref,
                self._search_dblp,
                self._search_openalex,
                self._search_semantic_scholar,
            ]
            for source_fn in sources:
                t0 = time.time()
                source_name = source_fn.__name__.replace("_search_", "")
                try:
                    papers = source_fn(client, query)
                    elapsed = time.time() - t0
                    if papers:
                        lines = []
                        for i, p in enumerate(papers):
                            authors = ", ".join(p.authors[:2]) if p.authors else ""
                            year = f"({p.year})" if p.year else ""
                            title = p.title[:100]
                            lines.append(f"  [{i+1}] {title} | {authors} {year}")
                        logger.info(
                            f"[AcademicClient] {source_name}: {len(papers)}条, {elapsed:.1f}s\n"
                            + "\n".join(lines)
                        )
                    else:
                        logger.info(f"[AcademicClient] {source_name}: 0条, {elapsed:.1f}s")
                    all_papers.extend(papers)
                except Exception as e:
                    logger.info(f"[AcademicClient] {source_name}: 失败 ({time.time()-t0:.1f}s) - {e}")

        # 去重（基于 title MD5）
        seen = set()
        unique = []
        for p in all_papers:
            title_hash = hashlib.md5(p.title.lower().strip().encode()).hexdigest()
            if title_hash not in seen:
                seen.add(title_hash)
                unique.append(p)

        result = unique[:max_results]
        self._save_cache(query, result)
        logger.info(f"[AcademicClient]检索完成: query='{query}', 去重后={len(unique)}, 返回={len(result)}")
        return result

    def _search_arxiv(self, client: httpx.Client, query: str) -> list[AcademicPaper]:
        url = "http://export.arxiv.org/api/query"
        resp = client.get(url, params={"search_query": f"all:{query}", "max_results": "5"})
        if resp.status_code != 200:
            return []

        papers = []
        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(resp.text)
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                authors = [a.find("atom:name", ns).text or "" for a in entry.findall("atom:author", ns)]
                papers.append(AcademicPaper(
                    title=title.text.strip() if title is not None and title.text else "",
                    authors=authors,
                    abstract=summary.text.strip()[:500] if summary is not None and summary.text else "",
                    url=entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else "",
                    source="arXiv",
                ))
        except Exception:
            pass
        return papers

    def _search_crossref(self, client: httpx.Client, query: str) -> list[AcademicPaper]:
        url = "https://api.crossref.org/works"
        resp = client.get(url, params={"query": query, "rows": "5"})
        if resp.status_code != 200:
            return []

        papers = []
        try:
            items = resp.json().get("message", {}).get("items", [])
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else ""
                authors = []
                for a in item.get("author", [])[:5]:
                    given = a.get("given", "")
                    family = a.get("family", "")
                    authors.append(f"{given} {family}".strip())
                year = str(item.get("created", {}).get("date-parts", [[None]])[0][0] or "")
                papers.append(AcademicPaper(
                    title=title,
                    authors=authors,
                    year=year,
                    doi=item.get("DOI", ""),
                    venue=", ".join(item.get("container-title", [])) if item.get("container-title") else "",
                    url=f"https://doi.org/{item.get('DOI', '')}" if item.get("DOI") else "",
                    source="Crossref",
                ))
        except Exception:
            pass
        return papers

    def _search_dblp(self, client: httpx.Client, query: str) -> list[AcademicPaper]:
        url = "https://dblp.org/search/publ/api"
        resp = client.get(url, params={"q": query, "format": "json", "h": "5"})
        if resp.status_code != 200:
            return []

        papers = []
        try:
            hits = resp.json().get("result", {}).get("hits", {}).get("hit", [])
            for hit in hits:
                info = hit.get("info", {})
                title = info.get("title", "")
                authors = []
                if isinstance(info.get("authors", {}).get("author"), list):
                    authors = [a.get("text", "") for a in info["authors"]["author"]]
                year = str(info.get("year", ""))
                papers.append(AcademicPaper(
                    title=title,
                    authors=authors,
                    year=year,
                    venue=info.get("venue", ""),
                    url=info.get("ee", info.get("url", "")),
                    source="DBLP",
                ))
        except Exception:
            pass
        return papers

    def _search_openalex(self, client: httpx.Client, query: str) -> list[AcademicPaper]:
        url = "https://api.openalex.org/works"
        resp = client.get(url, params={"search": query, "per_page": "5"})
        if resp.status_code != 200:
            return []

        papers = []
        try:
            results = resp.json().get("results", [])
            for item in results:
                title = item.get("title", "")
                authors = []
                for a in item.get("authorships", [])[:5]:
                    authors.append(a.get("author", {}).get("display_name", ""))
                abstract = ""
                if item.get("abstract_inverted_index"):
                    # OpenAlex 抽象索引需要重建
                    try:
                        idx = item["abstract_inverted_index"]
                        words = [""] * (max(max(v) for v in idx.values()) + 1)
                        for word, positions in idx.items():
                            for pos in positions:
                                words[pos] = word
                        abstract = " ".join(words)[:500]
                    except Exception:
                        pass
                papers.append(AcademicPaper(
                    title=title,
                    authors=authors,
                    year=str(item.get("publication_year", "")),
                    doi=item.get("doi", ""),
                    venue=item.get("primary_location", {}).get("source", {}).get("display_name", ""),
                    citation_count=item.get("cited_by_count", 0),
                    url=item.get("primary_location", {}).get("landing_page_url", ""),
                    source="OpenAlex",
                ))
        except Exception:
            pass
        return papers

    def _search_semantic_scholar(self, client: httpx.Client, query: str) -> list[AcademicPaper]:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        resp = client.get(url, params={"query": query, "limit": "5", "fields": "title,authors,year,abstract,citationCount,url"})
        if resp.status_code != 200:
            return []

        papers = []
        try:
            data = resp.json().get("data", [])
            for item in data:
                authors = [a.get("name", "") for a in item.get("authors", [])]
                papers.append(AcademicPaper(
                    title=item.get("title", ""),
                    authors=authors,
                    year=str(item.get("year", "")),
                    abstract=item.get("abstract", "")[:500] if item.get("abstract") else "",
                    citation_count=item.get("citationCount", 0) or 0,
                    url=item.get("url", ""),
                    source="Semantic Scholar",
                ))
        except Exception:
            pass
        return papers
