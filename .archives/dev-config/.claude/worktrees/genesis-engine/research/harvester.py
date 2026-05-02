"""Harvest module — source adapters and configuration loading."""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
import yaml
from duckduckgo_search import DDGS
from research.pipeline import Finding


logger = logging.getLogger(__name__)

# Rate limiting delays (seconds)
WEB_SEARCH_DELAY = 2.0
API_DELAY = 1.0


def load_config(path: str) -> dict[str, Any]:
    """Load and validate research config from YAML file."""
    config_path = Path(path)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if "focus_areas" not in config:
        raise ValueError("Config missing required field: focus_areas")

    for name, area in config["focus_areas"].items():
        queries = area.get("queries", [])
        if not queries:
            raise ValueError(f"Focus area '{name}' has no queries")

    return config


async def web_search_adapter(
    focus_areas: dict[str, Any],
) -> list[Finding]:
    """Search DuckDuckGo for each focus area's queries."""
    findings: list[Finding] = []

    with DDGS() as ddgs:
        for area_name, area in focus_areas.items():
            for query in area.get("queries", []):
                try:
                    results = ddgs.text(query, max_results=5)
                    for r in results:
                        findings.append(
                            Finding(
                                title=r.get("title", ""),
                                url=r.get("href", ""),
                                source="web_search",
                                snippet=r.get("body", ""),
                                category=area_name,
                            )
                        )
                    await asyncio.sleep(WEB_SEARCH_DELAY)
                except Exception as e:
                    logger.warning("Web search failed for query '%s': %s", query, e)

    return findings


async def hackernews_adapter(
    source_config: dict[str, Any],
    focus_areas: dict[str, Any],
) -> list[Finding]:
    """Fetch recent stories from HackerNews Algolia API."""
    findings: list[Finding] = []
    queries = source_config.get("queries", [])
    min_points = source_config.get("min_points", 10)
    tags = source_config.get("tags", ["story"])
    tag_str = ",".join(f"({t})" for t in tags) if tags else "(story)"

    for query in queries:
        try:
            resp = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "tags": tag_str, "numericFilters": f"points>{min_points}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for hit in data.get("hits", []):
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                findings.append(
                    Finding(
                        title=hit.get("title", ""),
                        url=url,
                        source="hackernews",
                        snippet=hit.get("title", ""),
                        category=_best_category(hit.get("title", ""), focus_areas),
                    )
                )

            await asyncio.sleep(API_DELAY)
        except Exception as e:
            logger.warning("HackerNews search failed for '%s': %s", query, e)

    return findings


async def reddit_adapter(
    source_config: dict[str, Any],
    focus_areas: dict[str, Any],
) -> list[Finding]:
    """Fetch posts from Reddit JSON API."""
    findings: list[Finding] = []
    subreddits = source_config.get("subreddits", [])
    sort = source_config.get("sort", "hot")
    limit = source_config.get("limit", 25)

    for sub in subreddits:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/{sort}.json",
                params={"limit": limit},
                headers={"User-Agent": "CohezionResearch/1.0"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                url = post.get("url", "")
                if not url or url.startswith("/"):
                    url = f"https://reddit.com{post.get('permalink', '')}"
                findings.append(
                    Finding(
                        title=post.get("title", ""),
                        url=url,
                        source="reddit",
                        snippet=post.get("selftext", "")[:300],
                        category=_best_category(post.get("title", ""), focus_areas),
                    )
                )

            await asyncio.sleep(API_DELAY)
        except Exception as e:
            logger.warning("Reddit fetch failed for r/%s: %s", sub, e)

    return findings


async def arxiv_adapter(
    source_config: dict[str, Any],
    focus_areas: dict[str, Any],
) -> list[Finding]:
    """Fetch recent papers from arXiv API."""
    findings: list[Finding] = []
    categories = source_config.get("categories", ["cs.AI"])
    max_results = source_config.get("max_results", 30)
    cat_query = "+OR+".join(f"cat:{c}" for c in categories)

    try:
        resp = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": cat_query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": max_results,
            },
            timeout=30,
        )
        resp.raise_for_status()

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)

        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns) or "").strip()
            summary = (entry.findtext("atom:summary", "", ns) or "").strip()
            link_el = entry.find("atom:link", ns)
            url = link_el.get("href", "") if link_el is not None else entry.findtext("atom:id", "", ns) or ""

            findings.append(
                Finding(
                    title=title,
                    url=url,
                    source="arxiv",
                    snippet=summary[:300],
                    category=_best_category(title + " " + summary, focus_areas),
                )
            )
    except Exception as e:
        logger.warning("arXiv fetch failed: %s", e)

    return findings


async def github_adapter(
    source_config: dict[str, Any],
    focus_areas: dict[str, Any],
) -> list[Finding]:
    """Fetch trending repos and releases from GitHub via gh CLI search API."""
    findings: list[Finding] = []

    # Recent popular repos by language
    languages = source_config.get("languages", ["python", "typescript"])
    for lang in languages:
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"language:{lang} created:>{date.today() - timedelta(days=7)}",
                    "sort": "stars",
                    "per_page": 10,
                },
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=15,
            )
            resp.raise_for_status()
            for repo in resp.json().get("items", []):
                findings.append(
                    Finding(
                        title=f"{repo.get('full_name', '')}: {repo.get('description', '')}",
                        url=repo.get("html_url", ""),
                        source="github_recent",
                        snippet=repo.get("description", "")[:300],
                        category=_best_category(repo.get("description", ""), focus_areas),
                    )
                )
            await asyncio.sleep(API_DELAY)
        except Exception as e:
            logger.warning("GitHub search failed for %s: %s", lang, e)

    # Release monitoring for tracked repos
    for repo_name in source_config.get("repos", [])[:20]:
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo_name}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if resp.status_code == 200:
                release = resp.json()
                findings.append(
                    Finding(
                        title=f"{repo_name} {release.get('tag_name', '')}: {release.get('name', '')}",
                        url=release.get("html_url", ""),
                        source="github_releases",
                        snippet=(release.get("body", "") or "")[:300],
                        category=_best_category(repo_name + " " + (release.get("body", "") or ""), focus_areas),
                    )
                )
            await asyncio.sleep(API_DELAY)
        except Exception as e:
            logger.warning("GitHub release check failed for %s: %s", repo_name, e)

    return findings


async def blog_feed_adapter(
    source_config: dict[str, Any],
    focus_areas: dict[str, Any],
) -> list[Finding]:
    """Check tracked blog URLs for new posts."""
    findings: list[Finding] = []
    urls = source_config.get("urls", [])

    for url in urls:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "CohezionResearch/1.0"})
            resp.raise_for_status()
            # Simple approach: extract title and first paragraph-like text
            text = resp.text[:5000]
            title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
            title = title_match.group(1) if title_match else url

            findings.append(
                Finding(
                    title=f"Blog: {title}",
                    url=url,
                    source="blog_feed",
                    snippet=f"Blog index page checked: {url}",
                    category=_best_category(title, focus_areas),
                )
            )
            await asyncio.sleep(API_DELAY)
        except Exception as e:
            logger.warning("Blog feed check failed for %s: %s", url, e)

    return findings


async def harvest(config: dict[str, Any]) -> list[Finding]:
    """Run all source adapters in parallel, collecting findings."""
    focus_areas = config.get("focus_areas", {})
    sources = config.get("sources", {})

    tasks: list[asyncio.Task] = []
    loop = asyncio.get_event_loop()

    # Always run web search
    tasks.append(asyncio.create_task(_safe_adapter("web_search", web_search_adapter(focus_areas))))

    # Run configured source adapters
    if "hackernews" in sources:
        tasks.append(
            asyncio.create_task(_safe_adapter("hackernews", hackernews_adapter(sources["hackernews"], focus_areas)))
        )
    if "reddit" in sources:
        tasks.append(asyncio.create_task(_safe_adapter("reddit", reddit_adapter(sources["reddit"], focus_areas))))
    if "arxiv" in sources:
        tasks.append(asyncio.create_task(_safe_adapter("arxiv", arxiv_adapter(sources["arxiv"], focus_areas))))
    if "github_recent" in sources or "github_releases" in sources:
        gh_config = {**sources.get("github_recent", {}), **sources.get("github_releases", {})}
        if "repos" not in gh_config and "github_releases" in sources:
            gh_config["repos"] = sources["github_releases"].get("repos", [])
        tasks.append(asyncio.create_task(_safe_adapter("github", github_adapter(gh_config, focus_areas))))
    if "blog_feeds" in sources:
        tasks.append(
            asyncio.create_task(_safe_adapter("blog_feeds", blog_feed_adapter(sources["blog_feeds"], focus_areas)))
        )

    results = await asyncio.gather(*tasks)

    all_findings: list[Finding] = []
    for result in results:
        if isinstance(result, list):
            all_findings.extend(result)

    logger.info("Harvest complete: %d total findings from %d adapters", len(all_findings), len(tasks))
    return all_findings


async def _safe_adapter(name: str, coro) -> list[Finding]:
    """Wrap an adapter coroutine so exceptions don't kill the gather."""
    try:
        return await coro
    except Exception as e:
        logger.error("Adapter '%s' failed: %s", name, e)
        return []


def _best_category(text: str, focus_areas: dict[str, Any]) -> str:
    """Simple keyword matching to pick the best focus area for a finding."""
    text_lower = text.lower()
    best_area = ""
    best_score = 0

    keywords = {
        "compound_engineering": [
            "compound",
            "knowledge graph",
            "decision record",
            "session memory",
            "pattern",
        ],
        "token_efficiency": [
            "token",
            "context window",
            "compression",
            "cache",
            "distillation",
            "efficiency",
        ],
        "context_awareness": ["context", "memory", "retrieval", "rag", "long context", "semantic"],
        "app_creation": ["agent", "mcp", "tool use", "framework", "code generation", "multi-agent"],
    }

    for area_name in focus_areas:
        area_keywords = keywords.get(area_name, [])
        score = sum(1 for kw in area_keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_area = area_name

    return best_area or next(iter(focus_areas), "unknown")
