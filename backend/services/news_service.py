"""News service — aggregates multiple RSS news feeds into a unified stream."""

import asyncio
import gzip
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("finance_app")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Feed definitions
# ---------------------------------------------------------------------------

RSS_FEEDS: list[dict] = [
    # Google News — top stories (aggregator, pulls from many sources)
    {"url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
     "default_source": "Google News", "has_source_tag": True},
    # Google News — business
    {"url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
     "default_source": "Google News", "has_source_tag": True},
    # Google News — world
    {"url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
     "default_source": "Google News", "has_source_tag": True},
    # Yahoo Finance — market & company news
    {"url": "https://finance.yahoo.com/news/rssindex",
     "default_source": "Yahoo Finance", "has_source_tag": False},
    # CNBC — top news
    {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
     "default_source": "CNBC", "has_source_tag": False},
    # CNBC — finance
    {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
     "default_source": "CNBC", "has_source_tag": False},
    # BBC — world news
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",
     "default_source": "BBC News", "has_source_tag": False},
    # BBC — business
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml",
     "default_source": "BBC News", "has_source_tag": False},
    # MarketWatch — top stories
    {"url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
     "default_source": "MarketWatch", "has_source_tag": False},
    # MarketWatch — market pulse
    {"url": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
     "default_source": "MarketWatch", "has_source_tag": False},
    # NPR — news
    {"url": "https://feeds.npr.org/1001/rss.xml",
     "default_source": "NPR", "has_source_tag": False},
    # Reuters — via Google News search (reliable fallback)
    {"url": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
     "default_source": "Reuters", "has_source_tag": True},
    # AP — via Google News search (reliable fallback)
    {"url": "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en",
     "default_source": "AP News", "has_source_tag": True},
]

# Cache
_MIN_FETCH_INTERVAL = 90  # seconds
_last_fetch_time: float = 0.0
_cached_articles: list[dict] = []

# ---------------------------------------------------------------------------
# HTTP + parsing helpers
# ---------------------------------------------------------------------------


def _fetch_url_sync(url: str, timeout: int = 12) -> bytes | None:
    """Fetch a single URL. Returns raw bytes or None on failure."""
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "gzip",
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw
    except (HTTPError, URLError, OSError) as exc:
        logger.warning("RSS fetch failed for %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.warning("RSS fetch error for %s: %s", url, exc)
        return None


def _parse_pubdate(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return date_str.strip()


def _clean_html(text: str) -> str:
    """Strip HTML tags and entities from text."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_single_feed(xml_bytes: bytes, feed_config: dict) -> list[dict]:
    """Parse one RSS feed into article dicts."""
    articles = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.debug("XML parse error for %s: %s", feed_config["default_source"], exc)
        return articles

    channel = root.find("channel")
    if channel is None:
        # Atom feed? Try direct item search
        items = root.findall("item")
    else:
        items = channel.findall("item")

    default_source = feed_config["default_source"]
    has_source_tag = feed_config.get("has_source_tag", False)

    for item in items:
        try:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue

            link = (item.findtext("link") or "").strip()
            raw_desc = (item.findtext("description") or "").strip()
            pub_date = _parse_pubdate(item.findtext("pubDate"))

            # Source: use <source> tag if available, else default
            if has_source_tag:
                source_el = item.find("source")
                source = (source_el.text.strip()
                          if source_el is not None and source_el.text
                          else default_source)
            else:
                source = default_source

            # Clean snippet
            snippet = _clean_html(raw_desc)
            snippet = re.sub(r"View Full Coverage on Google News\s*$", "", snippet).strip()
            if len(snippet) > 300:
                snippet = snippet[:297].rsplit(" ", 1)[0] + "..."

            # Clean source suffix from title
            clean_title = title
            if source and clean_title.endswith(f" - {source}"):
                clean_title = clean_title[: -(len(source) + 3)].strip()

            articles.append({
                "title": clean_title,
                "link": link,
                "source": source,
                "published": pub_date,
                "snippet": snippet,
            })
        except Exception as exc:
            logger.debug("Skipping malformed item in %s: %s", default_source, exc)
            continue

    return articles


# ---------------------------------------------------------------------------
# Article classification — weighted scoring engine
# ---------------------------------------------------------------------------
# Each keyword entry is (pattern, weight). Patterns use \b word boundaries
# to prevent false positives (e.g. "oil" won't match "soiled").
# Title matches get 2x weight boost since titles are more signal-dense.
# The category/region with the highest total score wins.
# ---------------------------------------------------------------------------

def _build_pattern(phrase: str) -> re.Pattern:
    """Compile a word-boundary regex for a keyword phrase."""
    escaped = re.escape(phrase)
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


def _build_rules(raw: list[tuple[str, list[tuple[str, float]]]]) -> list[tuple[str, list[tuple[re.Pattern, float]]]]:
    """Pre-compile all keyword patterns for a ruleset."""
    compiled = []
    for label, entries in raw:
        patterns = [(_build_pattern(phrase), weight) for phrase, weight in entries]
        compiled.append((label, patterns))
    return compiled


# ── Category keyword definitions ──
# (keyword_phrase, weight) — higher weight = stronger signal
_RAW_CATEGORY_RULES: list[tuple[str, list[tuple[str, float]]]] = [
    ("Markets", [
        # Core equity / index terms
        ("stock market", 3.0), ("stock exchange", 3.0), ("stocks", 2.0), ("stock", 1.5),
        ("equities", 2.5), ("equity market", 3.0),
        ("dow jones", 3.0), ("dow", 1.5), ("s&p 500", 3.0), ("s&p", 2.0),
        ("nasdaq", 2.5), ("russell 2000", 3.0), ("nikkei", 2.5), ("ftse", 2.5),
        ("dax", 2.0), ("hang seng", 2.5),
        ("wall street", 2.5), ("nyse", 2.5),
        # Share / price movement
        ("shares", 2.0), ("share price", 3.0), ("stock price", 3.0),
        ("shares slide", 3.0), ("shares rise", 3.0), ("shares fall", 3.0),
        ("shares surge", 3.0), ("shares drop", 3.0), ("shares tumble", 3.0),
        ("shares plunge", 3.0), ("shares rally", 3.0), ("shares jump", 3.0),
        ("surges", 1.5), ("plunges", 1.5), ("tumbles", 1.5), ("soars", 1.5),
        # Trading activity
        ("futures", 2.0), ("options", 1.0), ("derivatives", 2.0),
        ("rally", 1.5), ("selloff", 2.0), ("sell-off", 2.0), ("correction", 1.5),
        ("bull market", 3.0), ("bear market", 3.0), ("bull run", 2.5),
        ("market cap", 2.5), ("valuation", 1.5), ("overvalued", 2.0), ("undervalued", 2.0),
        ("market slump", 3.0), ("market crash", 3.0), ("market rout", 3.0),
        # Fixed income
        ("treasury", 1.5), ("treasuries", 2.0), ("bond market", 3.0), ("bonds", 1.5),
        ("bond yield", 3.0), ("yield curve", 3.0), ("10-year", 1.5),
        # Participants
        ("investor", 1.5), ("investors", 1.5), ("hedge fund", 2.5), ("mutual fund", 2.5),
        ("etf", 2.0), ("portfolio", 1.5), ("asset manager", 2.5),
        ("ipo", 2.5), ("spac", 2.0), ("listing", 1.0), ("delisting", 2.0),
        # Market events
        ("earnings", 2.0), ("quarterly results", 2.5), ("profit warning", 2.5),
        ("dividend", 2.0), ("share buyback", 2.5), ("buyback", 2.0),
        ("market volatility", 3.0), ("vix", 2.5), ("trading volume", 2.5),
        ("short selling", 2.5), ("margin call", 3.0),
        # Commodities
        ("commodity", 2.0), ("commodities", 2.0), ("gold price", 3.0),
        ("silver", 1.5), ("copper", 1.5), ("precious metals", 2.5),
        ("cocoa", 2.0), ("wheat", 1.5), ("corn", 1.5), ("soybeans", 1.5),
        ("coffee", 1.5), ("sugar", 1.0),
    ]),
    ("Technology", [
        # AI / ML
        ("artificial intelligence", 3.0), ("generative ai", 3.0), ("machine learning", 3.0),
        ("deep learning", 3.0), ("large language model", 3.0), ("llm", 2.5), ("chatgpt", 3.0),
        ("openai", 3.0), ("neural network", 2.5),
        # Semiconductors
        ("semiconductor", 3.0), ("semiconductors", 3.0), ("chip", 1.5), ("chipmaker", 3.0),
        ("chips", 1.0), ("microchip", 2.5), ("processor", 2.0), ("gpu", 2.5), ("cpu", 2.0),
        ("wafer", 2.0), ("foundry", 1.5), ("fab", 1.0), ("tsmc", 3.0),
        # Companies (high-signal tech names)
        ("nvidia", 3.0), ("apple", 1.5), ("google", 1.5), ("alphabet", 2.5),
        ("microsoft", 2.0), ("meta platforms", 3.0), ("amazon", 1.0),
        ("tesla", 2.0), ("intel", 2.0), ("amd", 2.0), ("qualcomm", 2.5),
        ("broadcom", 2.5), ("salesforce", 2.0), ("oracle", 1.5),
        ("tiktok", 2.0), ("bytedance", 2.5), ("spacex", 2.5),
        # Infrastructure
        ("cloud computing", 3.0), ("data center", 2.5), ("data centres", 2.5),
        ("cybersecurity", 3.0), ("cyber attack", 3.0), ("cyberattack", 3.0),
        ("data breach", 3.0), ("hack", 1.5), ("hacker", 2.0), ("ransomware", 3.0),
        # Emerging tech
        ("quantum computing", 3.0), ("quantum", 1.5), ("robotics", 2.5), ("robot", 1.5),
        ("autonomous vehicle", 3.0), ("self-driving", 3.0), ("ev", 1.5),
        ("electric vehicle", 2.5), ("blockchain", 2.0),
        ("5g", 2.0), ("6g", 2.0), ("satellite", 1.5), ("starlink", 2.5),
        # Software / industry
        ("software", 1.5), ("saas", 2.5), ("app", 1.0), ("platform", 1.0),
        ("startup", 1.5), ("tech industry", 3.0), ("silicon valley", 3.0),
        ("tech giant", 3.0), ("big tech", 3.0), ("tech sector", 3.0),
        ("social media", 2.0), ("streaming", 1.5),
        # AI (standalone) + consumer tech
        ("ai", 2.0), ("chatbot", 2.5), ("chatbots", 2.5), ("hallucination", 1.5),
        ("samsung", 2.0), ("galaxy", 1.5), ("iphone", 2.5), ("pixel", 1.5),
        ("waymo", 3.0), ("rivian", 3.0), ("lucid", 2.0),
        ("all-electric", 2.0), ("self driving", 3.0),
        ("brain-computer", 3.0), ("flying taxi", 3.0), ("flying taxis", 3.0),
        ("digital", 1.0), ("tech", 1.5),
    ]),
    ("Finance", [
        # Central banks / monetary policy
        ("federal reserve", 3.0), ("the fed", 2.5), ("fed chair", 3.0), ("powell", 2.5),
        ("central bank", 3.0), ("ecb", 2.5), ("bank of england", 3.0),
        ("bank of japan", 3.0), ("boj", 2.5), ("rbi", 2.0),
        ("interest rate", 3.0), ("rate hike", 3.0), ("rate cut", 3.0),
        ("monetary policy", 3.0), ("quantitative easing", 3.0), ("tightening", 1.5),
        ("basis points", 2.5), ("benchmark rate", 3.0),
        # Inflation / prices
        ("inflation", 2.5), ("deflation", 2.5), ("cpi", 2.5), ("pce", 2.5),
        ("consumer prices", 2.5), ("price index", 2.5), ("cost of living", 2.0),
        # Banking
        ("banking", 2.0), ("bank", 1.0), ("banks", 1.5), ("banker", 2.0),
        ("jpmorgan", 3.0), ("goldman sachs", 3.0), ("morgan stanley", 3.0),
        ("citigroup", 2.5), ("bank of america", 3.0), ("wells fargo", 2.5),
        ("credit suisse", 3.0), ("ubs", 2.0), ("hsbc", 2.0), ("deutsche bank", 3.0),
        ("deposit", 1.0), ("lending", 1.5), ("loan", 1.0), ("loans", 1.5),
        ("mortgage", 2.0), ("mortgage rate", 3.0), ("credit", 1.0),
        ("credit card", 2.0), ("debt", 1.5),
        # Fintech / crypto
        ("fintech", 3.0), ("cryptocurrency", 3.0), ("crypto", 2.0), ("bitcoin", 3.0),
        ("ethereum", 3.0), ("stablecoin", 3.0), ("defi", 2.5),
        ("digital currency", 3.0), ("cbdc", 3.0),
        # Currency
        ("forex", 3.0), ("exchange rate", 2.5), ("dollar", 1.5), ("euro", 1.0),
        ("yen", 1.5), ("yuan", 1.5), ("currency", 1.5), ("currencies", 2.0),
        # Insurance / regulation
        ("insurance", 1.5), ("insurer", 2.0), ("underwriting", 2.5),
        ("sec", 1.5), ("regulator", 1.5), ("compliance", 1.5),
        ("financial regulation", 3.0), ("dodd-frank", 3.0),
        # Corporate actions / distress
        ("bankruptcy", 3.0), ("chapter 11", 3.0), ("chapter 7", 3.0),
        ("liquidation", 2.5), ("insolvency", 2.5), ("restructuring", 2.0),
        ("merger", 2.5), ("acquisition", 2.5), ("takeover", 2.5),
        ("to acquire", 2.5), ("to buy", 1.0),
        ("m&a", 3.0), ("buyout", 2.5), ("private equity", 3.0),
        ("venture capital", 3.0), ("vc", 1.5),
        # Personal finance / retirement
        ("retirement", 2.5), ("retire", 2.0), ("retirees", 2.5), ("retiree", 2.5),
        ("social security", 3.0),
        ("401k", 3.0), ("ira", 2.0), ("pension", 2.5), ("annuity", 2.5),
        ("savings", 1.5), ("saving", 1.0), ("estate planning", 3.0),
        ("estate", 1.0), ("inheritance", 2.0), ("wealth", 1.5),
        ("financial planning", 3.0), ("financial advisor", 3.0),
        ("money market", 3.0), ("apy", 2.5), ("interest rates", 2.5),
        ("down payment", 2.5), ("buying power", 2.0),
        # Ratings / analysis
        ("downgrade", 2.5), ("upgrade", 1.5), ("rating", 1.5), ("ratings", 1.5),
        ("credit rating", 3.0), ("moody", 2.5), ("fitch", 2.5),
        ("profit", 1.5), ("revenue", 1.5), ("guidance", 2.0),
        ("berkshire hathaway", 3.0), ("warren buffett", 3.0), ("buffett", 2.5),
    ]),
    ("Economy", [
        # Macro indicators
        ("gdp", 2.5), ("gross domestic product", 3.0), ("economic growth", 3.0),
        ("economy", 2.0), ("economic", 1.5), ("recession", 3.0), ("depression", 2.5),
        ("stagflation", 3.0), ("soft landing", 3.0), ("hard landing", 3.0),
        # Labor market
        ("unemployment", 3.0), ("jobless", 2.5), ("nonfarm payrolls", 3.0),
        ("payrolls", 2.0), ("labor market", 3.0), ("hiring", 1.5),
        ("layoffs", 2.0), ("job cuts", 2.5), ("employment", 1.5),
        ("wages", 2.0), ("wage growth", 2.5), ("minimum wage", 2.5),
        ("workforce", 1.5), ("workers", 1.0), ("labor", 1.0),
        # Trade
        ("trade war", 3.0), ("trade deficit", 3.0), ("trade surplus", 3.0),
        ("tariff", 3.0), ("tariffs", 3.0), ("import duties", 3.0),
        ("sanctions", 2.0), ("embargo", 2.5), ("export", 1.5), ("imports", 1.5),
        ("free trade", 2.5), ("trade deal", 2.5), ("trade agreement", 2.5),
        ("trade bloc", 3.0), ("rare earth", 2.5), ("rare earths", 2.5),
        ("wto", 2.5), ("supply chain", 2.0), ("globalization", 2.0),
        # Consumer / housing
        ("consumer spending", 3.0), ("consumer confidence", 3.0),
        ("retail sales", 3.0), ("retail", 1.0), ("retailer", 2.0), ("retailers", 2.0),
        ("stores", 1.0), ("shopping", 1.0), ("e-commerce", 2.0), ("walmart", 2.0),
        ("target", 1.0), ("costco", 2.0), ("amazon", 1.0),
        ("housing market", 3.0), ("housing starts", 3.0), ("home sales", 2.5),
        ("home prices", 2.5), ("real estate", 2.0), ("property market", 2.5),
        ("rent", 1.5), ("rental", 1.5), ("eviction", 2.0),
        # Industry
        ("manufacturing", 2.0), ("pmi", 2.5), ("industrial output", 3.0),
        ("factory", 1.5), ("production", 1.0), ("supply", 1.0), ("demand", 1.0),
        ("shortage", 1.5), ("surplus", 1.5),
        # Fiscal
        ("budget", 1.5), ("deficit", 2.0), ("national debt", 3.0),
        ("government spending", 3.0), ("fiscal policy", 3.0), ("stimulus", 2.5),
        ("austerity", 2.5), ("tax", 1.0), ("taxes", 1.5), ("taxation", 2.0),
        # Corporate / business
        ("recall", 1.5), ("recalls", 1.5), ("price cap", 2.5), ("energy cap", 2.5),
        ("cost of living", 2.5), ("affordability", 2.0), ("price hike", 2.5),
        ("price rise", 2.0), ("price drop", 2.0), ("dynamic pricing", 3.0),
        ("cashless", 2.5), ("stamps", 1.0), ("postage", 1.5),
        ("wholesale", 2.0), ("inventories", 2.0), ("inventory", 1.5),
        ("ceo", 1.5), ("quarterly", 1.5),
    ]),
    ("Energy", [
        # Oil & gas
        ("crude oil", 3.0), ("oil prices", 3.0), ("oil price", 3.0),
        ("brent crude", 3.0), ("wti", 2.5), ("brent", 2.0),
        ("barrel", 2.0), ("barrels", 2.0), ("petroleum", 2.5),
        ("opec", 3.0), ("opec+", 3.0), ("oil production", 3.0),
        ("oil output", 3.0), ("oil supply", 3.0),
        ("natural gas", 3.0), ("lng", 2.5), ("shale", 2.5), ("fracking", 3.0),
        ("pipeline", 2.0), ("refinery", 2.5), ("refiner", 2.0), ("refining", 2.0),
        ("oil", 1.5), ("gasoline", 2.0), ("gas prices", 2.5), ("fuel", 1.5), ("diesel", 2.0),
        ("drilling", 2.0), ("offshore", 1.5), ("oil reserve", 3.0), ("oil flows", 3.0),
        ("energy crisis", 3.0),
        # Companies
        ("exxon", 3.0), ("exxonmobil", 3.0), ("chevron", 2.5), ("shell", 1.5),
        ("bp", 1.5), ("conocophillips", 3.0), ("totalenergies", 3.0),
        ("saudi aramco", 3.0), ("aramco", 2.5),
        # Renewables
        ("renewable energy", 3.0), ("renewables", 2.5), ("solar energy", 3.0),
        ("solar power", 3.0), ("solar panel", 2.5), ("wind energy", 3.0),
        ("wind power", 3.0), ("wind farm", 2.5), ("offshore wind", 3.0),
        ("clean energy", 3.0), ("green energy", 3.0),
        ("hydrogen", 2.0), ("nuclear energy", 3.0), ("nuclear power", 3.0),
        ("nuclear", 1.5), ("reactor", 1.5), ("uranium", 2.5),
        # Grid / utility
        ("power grid", 2.5), ("electricity", 2.0), ("utility", 1.5), ("utilities", 1.5),
        ("energy sector", 3.0), ("energy market", 3.0),
        ("carbon", 1.5), ("emissions", 2.0), ("climate change", 2.0),
        ("net zero", 2.5), ("carbon capture", 3.0),
    ]),
    ("Healthcare", [
        # Pharma / biotech
        ("pharmaceutical", 3.0), ("pharma", 2.5), ("biotech", 2.5), ("biotechnology", 3.0),
        ("drugmaker", 3.0), ("drug", 1.5), ("drugs", 1.0),
        ("medication", 2.0), ("prescription", 2.0), ("generic drug", 2.5),
        # Companies
        ("pfizer", 3.0), ("johnson & johnson", 3.0), ("moderna", 3.0),
        ("abbvie", 2.5), ("merck", 2.5), ("roche", 2.5), ("novartis", 2.5),
        ("eli lilly", 3.0), ("novo nordisk", 3.0), ("astrazeneca", 3.0),
        ("amgen", 2.5), ("gilead", 2.5), ("bristol-myers", 3.0),
        # Regulatory / trials
        ("fda", 3.0), ("fda approval", 3.0), ("clinical trial", 3.0),
        ("clinical trials", 3.0), ("phase 3", 2.5), ("phase 2", 2.0),
        ("drug trial", 3.0), ("ema", 2.0), ("drug approval", 3.0),
        # Conditions / treatment
        ("vaccine", 2.5), ("vaccination", 2.5), ("immunization", 2.5),
        ("cancer", 2.0), ("oncology", 3.0), ("tumor", 2.5), ("chemotherapy", 2.5),
        ("diabetes", 2.5), ("obesity", 2.0), ("alzheimer", 3.0), ("dementia", 2.0),
        ("heart disease", 2.5), ("cardiovascular", 2.5),
        ("hiv", 2.0), ("aids", 1.5), ("malaria", 2.0), ("tuberculosis", 2.0),
        ("pandemic", 2.5), ("epidemic", 2.5), ("outbreak", 2.0),
        ("covid", 2.0), ("coronavirus", 2.5),
        # Healthcare system
        ("hospital", 2.0), ("hospitals", 2.0), ("healthcare", 2.5), ("health care", 2.5),
        ("medical device", 3.0), ("medical devices", 3.0), ("medtech", 3.0),
        ("surgeon", 2.0), ("surgery", 1.5), ("transplant", 2.0),
        ("mental health", 2.5), ("public health", 2.5), ("who", 1.0),
        ("health insurance", 2.5), ("medicare", 2.5), ("medicaid", 2.5),
        ("opioid", 2.5), ("fentanyl", 2.5),
    ]),
    ("Politics", [
        # US political figures / institutions
        ("president", 1.5), ("presidential", 2.0), ("white house", 3.0),
        ("congress", 2.5), ("congressional", 2.5), ("senate", 2.0), ("senator", 2.0),
        ("house of representatives", 3.0), ("speaker of the house", 3.0),
        ("supreme court", 3.0), ("scotus", 3.0),
        ("democrat", 2.0), ("democrats", 2.0), ("democratic party", 3.0),
        ("republican", 2.0), ("republicans", 2.0), ("gop", 2.5),
        ("trump", 2.0), ("biden", 2.0), ("desantis", 2.5), ("vance", 2.0),
        # Elections / campaigns
        ("election", 2.5), ("elections", 2.5), ("vote", 1.0), ("voter", 1.5),
        ("voting", 1.5), ("ballot", 2.0), ("campaign", 1.5), ("polling", 2.0),
        ("primary", 1.0), ("caucus", 2.5), ("midterm", 2.5),
        ("electoral", 2.5), ("swing state", 3.0), ("battleground", 2.0),
        # Governance
        ("legislation", 2.5), ("executive order", 3.0), ("veto", 2.5),
        ("bipartisan", 2.5), ("filibuster", 3.0), ("impeach", 3.0),
        ("political", 1.5), ("politics", 2.0), ("partisan", 2.0),
        ("governor", 2.0), ("mayor", 1.5), ("attorney general", 2.5),
        ("cabinet", 1.5), ("nomination", 1.5), ("appointee", 2.0),
        # Policy
        ("policy", 1.0), ("regulation", 1.0), ("deregulation", 2.0),
        ("immigration", 2.5), ("border", 1.5), ("asylum", 2.0), ("deportation", 2.5),
        ("gun control", 3.0), ("second amendment", 3.0), ("gun law", 3.0),
        ("abortion", 2.5), ("roe v wade", 3.0),
        # Intelligence / justice
        ("fbi", 2.0), ("doj", 2.0), ("cia", 2.0), ("indictment", 2.5),
        ("prosecution", 2.0), ("subpoena", 2.5), ("investigation", 1.5),
        ("convicted", 2.0), ("acquitted", 2.5), ("trial", 1.0), ("verdict", 2.0),
        ("sentenced", 2.0), ("arraigned", 2.5), ("felony", 2.5), ("misdemeanor", 2.5),
        # Government / agencies
        ("government", 1.0), ("federal government", 2.5), ("state government", 2.5),
        ("tsa", 2.0), ("ice", 1.5), ("dhs", 2.0), ("homeland security", 2.5),
        ("epa", 2.0), ("fema", 2.5), ("irs", 2.0), ("nsa", 2.0),
        ("detention", 2.0), ("deportation", 2.5),
        ("shutdown", 2.0), ("government shutdown", 3.0),
        # International political figures
        ("putin", 2.0), ("xi jinping", 2.5), ("zelensky", 2.5),
        ("macron", 2.0), ("starmer", 2.0), ("modi", 2.0), ("netanyahu", 2.5),
        ("doge", 2.0), ("elon musk", 1.5),
        # Regime / leadership
        ("supreme leader", 3.0), ("regime", 2.5), ("authoritarian", 2.5),
        ("dictator", 2.5), ("leadership", 1.0), ("succession", 2.0),
        ("head of state", 2.5), ("prime minister", 2.0),
    ]),
    ("Defense", [
        # Military
        ("military", 2.5), ("armed forces", 3.0), ("troops", 2.5), ("soldiers", 2.0),
        ("army", 2.0), ("navy", 2.0), ("air force", 2.5), ("marines", 2.0),
        ("marine corps", 3.0), ("special forces", 3.0), ("national guard", 2.5),
        ("pentagon", 3.0), ("department of defense", 3.0),
        # Conflict
        ("war", 2.0), ("warfare", 2.5), ("combat", 2.5), ("battle", 1.5),
        ("invasion", 2.5), ("occupation", 2.0), ("siege", 2.0),
        ("airstrike", 3.0), ("airstrikes", 3.0), ("bombing", 2.5), ("bombardment", 2.5),
        ("shelling", 2.5), ("ground offensive", 3.0), ("ceasefire", 3.0),
        ("casualty", 2.0), ("casualties", 2.0), ("killed in action", 3.0),
        # Weapons / hardware
        ("missile", 2.5), ("missiles", 2.5), ("ballistic missile", 3.0),
        ("hypersonic", 3.0), ("icbm", 3.0), ("nuclear warhead", 3.0),
        ("nuclear weapon", 3.0), ("warhead", 3.0), ("drone strike", 3.0),
        ("drone", 1.5), ("drones", 1.5), ("fighter jet", 3.0), ("f-35", 3.0),
        ("submarine", 2.5), ("aircraft carrier", 3.0), ("warship", 3.0),
        ("tank", 1.5), ("artillery", 2.5), ("ammunition", 2.5), ("munitions", 2.5),
        ("weapons", 2.0), ("arms deal", 3.0), ("arms sales", 3.0),
        # Alliances / organizations
        ("nato", 3.0), ("aukus", 3.0), ("defense pact", 3.0),
        ("defense spending", 3.0), ("military budget", 3.0),
        ("arms race", 3.0), ("nuclear proliferation", 3.0),
        ("peacekeeping", 2.5), ("deployment", 2.0),
        # Active conflict verbs / patterns
        ("strike", 1.5), ("strikes", 1.5), ("targeted", 1.5),
        ("death toll", 3.0), ("killed", 1.5), ("kills", 1.5),
        ("attacked", 1.5), ("attacks", 1.5), ("attack", 1.5),
        ("evacuate", 2.0), ("evacuation", 2.0), ("evacuations", 2.0), ("evacuees", 2.5),
        ("retaliation", 2.5), ("retaliatory", 2.5), ("escalation", 2.0),
        ("de-escalation", 2.5), ("conflict", 2.0), ("hostilities", 2.5),
        ("offensive", 1.5), ("defensive", 1.5), ("incursion", 2.5),
        ("airspace", 2.5), ("no-fly zone", 3.0),
        ("projectile", 3.0), ("intercepted", 2.5), ("retaliate", 2.5),
        # Intelligence / security
        ("intelligence agency", 3.0), ("espionage", 3.0), ("spy", 2.0),
        ("counterterrorism", 3.0), ("terrorism", 2.5), ("terrorist", 2.5),
        ("insurgent", 2.5), ("insurgency", 2.5), ("militia", 2.5),
        # Named conflicts / equipment
        ("idf", 3.0), ("hezbollah", 3.0), ("hamas", 2.5),
        ("houthi", 3.0), ("houthis", 3.0),
        ("shahed", 3.0), ("iron dome", 3.0),
    ]),
    ("World", [
        # International relations
        ("diplomat", 2.0), ("diplomacy", 2.5), ("diplomatic", 2.0),
        ("united nations", 3.0), ("un general assembly", 3.0), ("un security council", 3.0),
        ("summit", 1.5), ("bilateral", 2.0), ("multilateral", 2.0),
        ("foreign minister", 2.5), ("foreign affairs", 2.5), ("ambassador", 2.0),
        ("treaty", 2.0), ("accord", 1.5), ("geopolitical", 3.0), ("geopolitics", 3.0),
        # Conflicts / crises (region-agnostic)
        ("refugee", 2.5), ("refugees", 2.5), ("humanitarian", 2.5),
        ("humanitarian crisis", 3.0), ("displacement", 2.0), ("migration", 2.0),
        ("coup", 2.5), ("civil war", 3.0), ("uprising", 2.5), ("revolution", 2.0),
        ("protest", 1.5), ("protests", 1.5), ("unrest", 2.0),
        # International organizations
        ("world bank", 3.0), ("imf", 2.5), ("international monetary fund", 3.0),
        ("g7", 2.5), ("g20", 2.5), ("brics", 2.5), ("asean", 2.5),
        ("european union", 3.0), ("african union", 3.0),
        # Global issues
        ("climate summit", 3.0), ("cop28", 3.0), ("cop29", 3.0),
        ("global warming", 2.5), ("paris agreement", 3.0),
        ("food crisis", 3.0), ("famine", 2.5), ("drought", 2.0), ("flood", 1.5),
        ("earthquake", 2.0), ("tsunami", 2.5), ("natural disaster", 2.5),
        ("aid", 1.0), ("foreign aid", 2.5), ("humanitarian aid", 3.0),
    ]),
    ("Sports", [
        # General sports
        ("sports", 2.0), ("athlete", 2.0), ("athletes", 2.0), ("championship", 2.0),
        ("tournament", 2.0), ("playoff", 2.5), ("playoffs", 2.5), ("semifinal", 2.5),
        ("quarterfinal", 2.5), ("final", 1.0), ("finals", 1.5),
        ("season", 1.0), ("coach", 1.5), ("roster", 2.5), ("draft", 2.0),
        ("mvp", 2.5), ("all-star", 2.5), ("hall of fame", 3.0),
        ("score", 1.0), ("scores", 1.0), ("win", 1.0), ("loss", 1.0),
        ("victory", 1.0), ("defeat", 1.0),
        # US major leagues
        ("nfl", 3.0), ("nba", 3.0), ("mlb", 3.0), ("nhl", 3.0), ("mls", 2.5),
        ("super bowl", 3.0), ("world series", 3.0), ("stanley cup", 3.0),
        ("march madness", 3.0), ("ncaa", 3.0),
        # Football (American)
        ("quarterback", 3.0), ("touchdown", 3.0), ("football", 2.0),
        ("chiefs", 2.0), ("eagles", 1.5), ("cowboys", 2.0), ("49ers", 2.5),
        ("patriots", 1.5), ("packers", 2.0),
        # Basketball
        ("basketball", 2.5), ("lakers", 2.5), ("celtics", 2.0), ("warriors", 2.0),
        ("cavaliers", 2.0), ("cavs", 2.0), ("knicks", 2.5),
        ("lebron", 3.0), ("lebron james", 3.0), ("steph curry", 3.0),
        # Baseball
        ("baseball", 2.5), ("home run", 2.5), ("pitcher", 2.0), ("batting", 2.0),
        ("innings", 2.5), ("strikeout", 2.5), ("world classic", 2.5),
        # Soccer/Football
        ("premier league", 3.0), ("la liga", 3.0), ("bundesliga", 3.0),
        ("serie a", 2.5), ("champions league", 3.0), ("fa cup", 3.0),
        ("soccer", 2.5), ("footballer", 2.5), ("goal", 1.0), ("goalkeeper", 2.5),
        ("var", 2.0), ("offside", 2.5), ("penalty kick", 3.0),
        ("fifa", 3.0), ("world cup", 3.0), ("uefa", 3.0),
        ("manchester united", 3.0), ("liverpool", 2.0), ("arsenal", 2.5),
        ("chelsea", 2.0), ("real madrid", 3.0), ("barcelona", 2.0),
        # Tennis / golf / boxing / mma
        ("tennis", 2.5), ("grand slam", 2.5), ("wimbledon", 3.0),
        ("golf", 2.0), ("pga", 3.0), ("masters", 1.5),
        ("boxing", 2.5), ("ufc", 3.0), ("mma", 3.0), ("heavyweight", 2.5),
        # Racing
        ("formula 1", 3.0), ("formula one", 3.0), ("f1", 2.5), ("nascar", 3.0), ("grand prix", 3.0),
        # Cycling
        ("tour de france", 3.0), ("giro", 2.0), ("cycling", 2.5), ("peloton", 2.0),
        # Olympics
        ("olympics", 3.0), ("olympic", 2.5), ("medal", 1.5), ("gold medal", 2.5),
        # Other sports
        ("cricket", 2.5), ("rugby", 2.5), ("hockey", 2.0),
        ("swimming", 1.5), ("track and field", 3.0), ("marathon", 2.0),
        # Player transactions
        ("free agent", 2.5), ("free agency", 2.5), ("trade deadline", 3.0),
        ("contract extension", 2.5), ("extension", 1.0), ("signing", 1.5),
        ("transfer", 1.5), ("transfer window", 3.0),
        # Fantasy / betting
        ("fantasy football", 3.0), ("fantasy sports", 3.0),
        ("sportsbook", 3.0), ("odds", 1.5), ("betting", 2.0),
    ]),
    ("Entertainment", [
        # Film / TV
        ("movie", 2.0), ("movies", 2.0), ("film", 1.5), ("box office", 3.0),
        ("cinema", 2.5), ("hollywood", 2.5), ("blockbuster", 2.5),
        ("oscar", 2.5), ("oscars", 2.5), ("academy award", 3.0),
        ("emmy", 2.5), ("emmys", 2.5), ("golden globe", 3.0),
        ("pixar", 3.0), ("disney", 2.0), ("marvel", 2.5), ("netflix", 2.0),
        ("hbo", 2.0), ("streaming", 1.5), ("tv show", 2.5), ("series", 1.0),
        ("premiere", 1.5), ("sequel", 2.0), ("remake", 2.0),
        ("director", 1.5), ("actor", 1.5), ("actress", 2.0),
        # Music
        ("music", 1.5), ("musician", 2.0), ("concert", 2.0), ("tour", 1.0),
        ("album", 2.0), ("grammy", 3.0), ("grammys", 3.0),
        ("billboard", 2.0), ("hip hop", 2.5), ("rap", 1.5), ("pop music", 2.5),
        ("singer", 2.0), ("rapper", 2.5), ("band", 1.0),
        # Celebrity / pop culture
        ("celebrity", 2.5), ("celebrities", 2.5), ("fame", 1.0), ("viral", 1.5),
        ("reality tv", 3.0), ("reality show", 3.0), ("red carpet", 2.5),
        ("paparazzi", 3.0), ("tabloid", 2.5), ("scandal", 1.5),
        # Gaming
        ("video game", 3.0), ("video games", 3.0), ("gaming", 2.0),
        ("playstation", 3.0), ("xbox", 3.0), ("nintendo", 3.0),
        ("esports", 3.0), ("twitch", 2.0),
        # Books / arts
        ("bestseller", 2.5), ("author", 1.5), ("novel", 1.5), ("book", 1.0),
        ("exhibition", 1.5), ("museum", 1.5), ("gallery", 1.0),
        ("broadway", 3.0), ("theater", 1.5), ("theatre", 1.5),
        # Notable names (entertainment-specific, weighted carefully)
        ("rihanna", 3.0), ("beyonce", 3.0), ("taylor swift", 3.0),
        ("drake", 2.0), ("kanye", 2.5), ("kardashian", 3.0),
        ("travis kelce", 2.5),
        # TV shows as entertainment signals
        ("top model", 2.5), ("deadliest catch", 3.0), ("survivor", 1.5),
        ("bachelor", 1.5), ("bachelorette", 2.5), ("idol", 1.5),
        ("got talent", 2.5), ("dancing with the stars", 3.0),
    ]),
]

# ── Region keyword definitions ──
_RAW_REGION_RULES: list[tuple[str, list[tuple[str, float]]]] = [
    ("US", [
        # Direct references
        ("united states", 3.0), ("u.s.", 3.0), ("u.s.a.", 3.0),
        ("american", 1.5), ("americans", 2.0),
        # Institutions
        ("congress", 2.0), ("white house", 3.0), ("pentagon", 2.5),
        ("capitol hill", 3.0), ("oval office", 3.0),
        ("federal", 1.0), ("fed", 1.0), ("federal reserve", 2.5),
        ("wall street", 2.5), ("nasdaq", 2.0), ("nyse", 2.5), ("sec", 1.5),
        ("fbi", 2.0), ("cia", 2.0), ("doj", 2.0), ("fda", 1.5),
        # Political
        ("democrat", 1.5), ("republican", 1.5), ("gop", 2.0),
        ("trump", 1.5), ("biden", 1.5),
        # Cities / states
        ("washington d.c.", 3.0), ("new york", 1.5), ("los angeles", 1.5),
        ("california", 2.0), ("texas", 2.0), ("florida", 2.0),
        ("chicago", 1.5), ("san francisco", 1.5), ("seattle", 1.5),
        ("silicon valley", 2.0), ("hollywood", 1.5), ("boston", 1.0),
        ("michigan", 1.5), ("ohio", 1.5), ("pennsylvania", 1.5),
        ("virginia", 1.0), ("georgia", 1.0), ("arizona", 1.5), ("nevada", 1.5),
        ("hawaii", 2.0), ("alaska", 2.0),
        # Finance
        ("dow jones", 2.0), ("s&p 500", 2.0),
        # Companies as US signals
        ("boeing", 1.5), ("lockheed", 1.5),
    ]),
    ("Europe", [
        # Continental
        ("europe", 2.5), ("european", 2.0), ("european union", 3.0), ("eu", 1.5),
        ("eurozone", 3.0), ("ecb", 2.5), ("brussels", 2.5), ("strasbourg", 2.5),
        # UK
        ("united kingdom", 3.0), ("britain", 2.5), ("british", 2.0),
        ("england", 2.0), ("scotland", 2.0), ("wales", 2.0), ("northern ireland", 2.5),
        ("london", 2.0), ("downing street", 3.0), ("parliament", 1.5),
        ("nhs", 2.5), ("bank of england", 3.0), ("ftse", 2.5), ("bbc", 1.0),
        ("starmer", 2.5), ("sunak", 2.5), ("brexit", 3.0),
        # France
        ("france", 2.5), ("french", 2.0), ("paris", 1.5), ("macron", 2.5),
        ("elysee", 3.0),
        # Germany
        ("germany", 2.5), ("german", 2.0), ("berlin", 2.0), ("bundesbank", 3.0),
        ("merkel", 2.5), ("scholz", 2.5), ("dax", 2.0),
        # Other
        ("italy", 2.0), ("italian", 2.0), ("rome", 1.5), ("milan", 1.5),
        ("spain", 2.0), ("spanish", 2.0), ("madrid", 1.5), ("barcelona", 1.5),
        ("netherlands", 2.0), ("dutch", 2.0), ("amsterdam", 2.0),
        ("belgium", 2.0), ("sweden", 2.0), ("norway", 2.0), ("denmark", 2.0),
        ("finland", 2.0), ("switzerland", 2.0), ("swiss", 2.0), ("zurich", 2.0),
        ("austria", 2.0), ("vienna", 1.5), ("poland", 2.0), ("czech", 2.0),
        ("portugal", 2.0), ("greece", 2.0), ("athens", 1.5),
        ("ukraine", 2.0), ("ukrainian", 2.0), ("kyiv", 2.5),
        ("romania", 2.0), ("hungary", 2.0), ("budapest", 2.0),
        ("baltic", 2.0), ("balkan", 2.0), ("scandinavia", 2.0),
    ]),
    ("Asia", [
        # Continental
        ("asia", 2.0), ("asian", 2.0), ("asia-pacific", 2.5),
        # China
        ("china", 2.5), ("chinese", 2.0), ("beijing", 2.5), ("shanghai", 2.0),
        ("hong kong", 2.5), ("xi jinping", 3.0), ("ccp", 2.5),
        ("pla", 2.5), ("shenzhen", 2.0), ("guangzhou", 2.0),
        ("taiwan", 2.5), ("taiwanese", 2.5), ("taipei", 2.5),
        # Japan
        ("japan", 2.5), ("japanese", 2.0), ("tokyo", 2.5),
        ("nikkei", 2.5), ("bank of japan", 3.0), ("boj", 2.5), ("yen", 2.0),
        # Korea
        ("south korea", 2.5), ("north korea", 2.5), ("korean", 2.0),
        ("seoul", 2.5), ("pyongyang", 3.0), ("kim jong", 3.0),
        # India
        ("india", 2.5), ("indian", 2.0), ("new delhi", 2.5), ("delhi", 2.0),
        ("mumbai", 2.0), ("modi", 2.0), ("rbi", 2.0), ("rupee", 2.5),
        # Southeast Asia
        ("singapore", 2.5), ("vietnam", 2.0), ("indonesia", 2.0),
        ("malaysia", 2.0), ("philippines", 2.0), ("thailand", 2.0),
        ("myanmar", 2.5), ("cambodia", 2.0), ("asean", 2.5), ("bangkok", 2.0),
        # Central Asia / Pacific
        ("australia", 2.0), ("australian", 2.0), ("sydney", 1.5),
        ("new zealand", 2.0), ("pakistan", 2.0), ("bangladesh", 2.0),
        ("afghanistan", 2.5), ("kabul", 2.5), ("sri lanka", 2.5),
    ]),
    ("Middle East", [
        ("middle east", 3.0), ("mideast", 3.0),
        # Countries
        ("iran", 2.5), ("iranian", 2.5), ("tehran", 2.5), ("ayatollah", 3.0),
        ("iraq", 2.5), ("iraqi", 2.5), ("baghdad", 2.5),
        ("israel", 2.5), ("israeli", 2.5), ("tel aviv", 2.5), ("jerusalem", 2.0),
        ("netanyahu", 2.5), ("idf", 3.0), ("hamas", 3.0), ("hezbollah", 3.0),
        ("gaza", 3.0), ("west bank", 3.0), ("palestinian", 2.5),
        ("saudi arabia", 3.0), ("saudi", 2.5), ("riyadh", 2.5),
        ("qatar", 2.5), ("doha", 2.5),
        ("uae", 2.5), ("abu dhabi", 2.5), ("dubai", 2.5),
        ("bahrain", 2.5), ("oman", 2.5), ("kuwait", 2.5),
        ("syria", 2.5), ("syrian", 2.5), ("damascus", 2.5),
        ("lebanon", 2.5), ("beirut", 2.5),
        ("yemen", 2.5), ("houthi", 3.0), ("houthis", 3.0),
        ("jordan", 2.0), ("amman", 2.5),
        ("turkey", 2.0), ("turkish", 2.0), ("ankara", 2.5), ("istanbul", 2.0),
        ("erdogan", 2.5),
        # Waterways
        ("persian gulf", 3.0), ("strait of hormuz", 3.0), ("red sea", 2.5),
        ("suez canal", 3.0), ("bab el-mandeb", 3.0),
    ]),
    ("Americas", [
        ("latin america", 3.0), ("south america", 3.0), ("central america", 3.0),
        ("caribbean", 2.5),
        # Countries
        ("brazil", 2.5), ("brazilian", 2.5), ("sao paulo", 2.5), ("brasilia", 2.5),
        ("lula", 2.5), ("bolsonaro", 2.5),
        ("mexico", 2.5), ("mexican", 2.5), ("mexico city", 2.5),
        ("canada", 2.5), ("canadian", 2.0), ("ottawa", 2.0), ("toronto", 2.0),
        ("trudeau", 2.5), ("alberta", 2.0), ("quebec", 2.0),
        ("argentina", 2.5), ("milei", 2.5), ("buenos aires", 2.5),
        ("colombia", 2.5), ("bogota", 2.5),
        ("chile", 2.5), ("santiago", 2.0),
        ("peru", 2.5), ("lima", 2.0),
        ("venezuela", 2.5), ("maduro", 3.0), ("caracas", 2.5),
        ("cuba", 2.5), ("havana", 2.5),
        ("ecuador", 2.5), ("panama", 2.5), ("costa rica", 2.5),
        ("guatemala", 2.5), ("honduras", 2.5), ("el salvador", 2.5),
    ]),
    ("Africa", [
        ("africa", 2.5), ("african", 2.5), ("sub-saharan", 3.0),
        # Countries
        ("nigeria", 2.5), ("nigerian", 2.5), ("lagos", 2.5), ("abuja", 2.5),
        ("south africa", 3.0), ("johannesburg", 2.5), ("cape town", 2.5),
        ("kenya", 2.5), ("nairobi", 2.5),
        ("egypt", 2.5), ("egyptian", 2.5), ("cairo", 2.5),
        ("ethiopia", 2.5), ("addis ababa", 2.5),
        ("congo", 2.5), ("kinshasa", 2.5),
        ("sudan", 2.5), ("south sudan", 3.0), ("khartoum", 2.5),
        ("somalia", 2.5), ("mogadishu", 2.5),
        ("tanzania", 2.5), ("uganda", 2.5), ("ghana", 2.5),
        ("mozambique", 2.5), ("angola", 2.5), ("zimbabwe", 2.5),
        ("morocco", 2.5), ("tunisia", 2.5), ("algeria", 2.5), ("libya", 2.5),
        ("sahel", 3.0), ("sahara", 2.0),
        ("african union", 3.0),
    ]),
]

# Pre-compile all patterns at module load
_CATEGORY_RULES = _build_rules(_RAW_CATEGORY_RULES)
_REGION_RULES = _build_rules(_RAW_REGION_RULES)

# Minimum score threshold — below this, classify as General / Global
_CATEGORY_MIN_SCORE = 2.0
_REGION_MIN_SCORE = 2.0

# Title match multiplier — keywords found in the title carry more weight
_TITLE_BOOST = 2.0


def _score_all(
    text: str,
    category_rules: list[tuple[str, list[tuple[re.Pattern, float]]]],
    region_rules: list[tuple[str, list[tuple[re.Pattern, float]]]],
) -> tuple[dict[str, float], dict[str, float]]:
    """Score text against both category and region rules in one pass."""
    cat_scores: dict[str, float] = {}
    reg_scores: dict[str, float] = {}

    for label, patterns in category_rules:
        total = 0.0
        for pat, weight in patterns:
            if pat.search(text):
                total += weight
        if total > 0:
            cat_scores[label] = total

    for label, patterns in region_rules:
        total = 0.0
        for pat, weight in patterns:
            if pat.search(text):
                total += weight
        if total > 0:
            reg_scores[label] = total

    return cat_scores, reg_scores


def _classify_article(article: dict) -> None:
    """Add category and region fields to an article dict (in-place).

    Uses weighted scoring with title boost. The label with the highest
    cumulative score wins, provided it exceeds the minimum threshold.
    """
    title = article.get("title", "")
    snippet = article.get("snippet", "")
    full_text = f"{title} {snippet}"

    # Single pass over full text
    cat_full, reg_full = _score_all(full_text, _CATEGORY_RULES, _REGION_RULES)
    # Single pass over title (for boost)
    cat_title, reg_title = _score_all(title, _CATEGORY_RULES, _REGION_RULES)

    # Merge with title boost
    cat_scores: dict[str, float] = {}
    for label in set(cat_full) | set(cat_title):
        cat_scores[label] = cat_full.get(label, 0) + cat_title.get(label, 0) * _TITLE_BOOST

    reg_scores: dict[str, float] = {}
    for label in set(reg_full) | set(reg_title):
        reg_scores[label] = reg_full.get(label, 0) + reg_title.get(label, 0) * _TITLE_BOOST

    # Pick best category
    if cat_scores:
        best_cat = max(cat_scores, key=cat_scores.get)
        if cat_scores[best_cat] >= _CATEGORY_MIN_SCORE:
            article["category"] = best_cat
        else:
            article["category"] = "General"
    else:
        article["category"] = "General"

    # Pick best region
    if reg_scores:
        best_reg = max(reg_scores, key=reg_scores.get)
        if reg_scores[best_reg] >= _REGION_MIN_SCORE:
            article["region"] = best_reg
        else:
            article["region"] = "Global"
    else:
        article["region"] = "Global"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())[:80]


def _title_words(title: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9\s]", "", title.lower()).split())


class NewsService:
    """Aggregates news from multiple RSS feeds with DB persistence."""

    def __init__(self, news_repo=None):
        self._repo = news_repo
        self._fetch_lock = asyncio.Lock()
        self._company_locks: dict[str, asyncio.Lock] = {}
        self._last_prune = 0.0

    async def _persist_articles(self, articles: list[dict]) -> None:
        try:
            count = await self._repo.upsert_articles(articles)
            logger.info("Persisted %d articles to DB", count)
        except Exception:
            logger.exception("Failed to persist articles to DB")

    async def _prune_old_articles(self) -> None:
        try:
            count = await self._repo.prune_old(keep_days=30)
            if count > 0:
                logger.info("Pruned %d old news articles", count)
        except Exception:
            logger.exception("Failed to prune old articles")

    async def get_top_news(self, limit: int = 2000, days: int = 10) -> list[dict]:
        """Return news articles from the last N days.

        Flow:
        1. Trigger a background RSS refresh if the in-memory cache is stale.
        2. Return articles from the DB (which has accumulated history).
        3. If no DB repo, fall back to in-memory only.
        """
        global _last_fetch_time, _cached_articles

        async with self._fetch_lock:
            now = time.monotonic()
            stale = not _cached_articles or (now - _last_fetch_time) >= _MIN_FETCH_INTERVAL

            if stale:
                try:
                    fresh = await self._fetch_all_feeds()
                    _cached_articles = fresh
                    _last_fetch_time = now
                    logger.info("Aggregated %d news articles from %d feeds",
                                len(fresh), len(RSS_FEEDS))

                    # Persist to DB in background (non-blocking for the response)
                    if self._repo and fresh:
                        asyncio.create_task(self._persist_articles(fresh))

                    # Periodically prune old articles
                    if self._repo:
                        now_mono = time.monotonic()
                        if now_mono - self._last_prune > 3600:
                            self._last_prune = now_mono
                            asyncio.create_task(self._prune_old_articles())
                except Exception as exc:
                    logger.error("News aggregation failed: %s", exc)

        # Serve from DB if available (has historical depth)
        if self._repo:
            try:
                db_articles = await self._repo.get_articles(days=days, limit=limit)
                if db_articles:
                    # Remap DB column names to API field names
                    result = []
                    for row in db_articles:
                        result.append({
                            "title": row["title"],
                            "link": row["url"],
                            "source": row["source"],
                            "published": row["published_at"],
                            "snippet": row.get("snippet", ""),
                            "category": row.get("category", "General"),
                            "region": row.get("region", "Global"),
                            "coverage_count": row.get("coverage_count", 1),
                        })
                    return result
            except Exception as exc:
                logger.warning("DB read failed, falling back to cache: %s", exc)

        # Fallback: in-memory cache only
        return _cached_articles[:limit]

    async def _fetch_all_feeds(self) -> list[dict]:
        """Fetch all RSS feeds in parallel, merge, dedupe, sort."""

        async def _fetch_one(feed: dict) -> list[dict]:
            xml = await asyncio.to_thread(_fetch_url_sync, feed["url"])
            if xml is None:
                return []
            return _parse_single_feed(xml, feed)

        # Fetch all feeds concurrently
        results = await asyncio.gather(
            *[_fetch_one(f) for f in RSS_FEEDS],
            return_exceptions=True,
        )

        all_articles: list[dict] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Feed %s failed: %s",
                               RSS_FEEDS[i]["default_source"], result)
                continue
            count = len(result)
            if count > 0:
                logger.debug("Got %d articles from %s",
                             count, RSS_FEEDS[i]["default_source"])
            all_articles.extend(result)

        # --- Deduplicate with coverage scoring ---
        # First pass: exact title dedup + count sources per story
        key_to_article: dict[str, dict] = {}
        key_to_sources: dict[str, set[str]] = {}
        for a in all_articles:
            key = _title_key(a["title"])
            if key not in key_to_article:
                key_to_article[key] = a
                key_to_sources[key] = set()
            key_to_sources[key].add(a.get("source", ""))

        # Second pass: fuzzy match — group articles with 45%+ word overlap
        keys = list(key_to_article.keys())
        # Pre-compute word sets
        key_to_words = {k: _title_words(key_to_article[k]["title"]) for k in keys}
        merged: dict[str, str] = {}
        for i, k1 in enumerate(keys):
            if k1 in merged:
                continue
            words1 = key_to_words[k1]
            if len(words1) < 3:
                continue
            for k2 in keys[i + 1:]:
                if k2 in merged:
                    continue
                words2 = key_to_words[k2]
                if len(words2) < 3:
                    continue
                overlap = len(words1 & words2)
                min_len = min(len(words1), len(words2))
                if min_len > 0 and overlap / min_len >= 0.45:
                    merged[k2] = k1
                    key_to_sources[k1] |= key_to_sources.get(k2, set())

        # Build final list with coverage_count
        unique: list[dict] = []
        for key, article in key_to_article.items():
            if key in merged:
                continue
            sources = key_to_sources.get(key, set())
            article["coverage_count"] = len(sources)
            unique.append(article)

        # Classify each article
        for a in unique:
            _classify_article(a)

        # Sort by published date, newest first
        def sort_key(article: dict) -> float:
            pub = article.get("published")
            if not pub:
                return 0.0
            try:
                dt = datetime.fromisoformat(pub)
                return dt.timestamp()
            except Exception:
                return 0.0

        unique.sort(key=sort_key, reverse=True)

        return unique

    # ------------------------------------------------------------------
    # Company-specific news
    # ------------------------------------------------------------------

    _company_cache: dict[str, tuple[float, list[dict]]] = {}
    _COMPANY_CACHE_TTL = 120  # seconds

    async def get_company_news(
        self, ticker: str, company_name: str | None = None, limit: int = 200
    ) -> list[dict]:
        """Fetch news for a specific company via Google News RSS search.

        Searches by both ticker and company name for broader coverage.
        Results are classified and returned sorted by date.
        """
        cache_key = ticker.upper()

        # Check in-memory cache (outside lock — read-only fast path)
        now = time.monotonic()
        if cache_key in self._company_cache:
            cached_time, cached_articles = self._company_cache[cache_key]
            if (now - cached_time) < self._COMPANY_CACHE_TTL:
                return cached_articles[:limit]

        # Per-ticker lock to prevent thundering herd
        if ticker not in self._company_locks:
            self._company_locks[ticker] = asyncio.Lock()
        async with self._company_locks[ticker]:
            # Check cache again (another request may have populated it while we waited)
            now = time.monotonic()
            if cache_key in self._company_cache:
                cached_time, cached_articles = self._company_cache[cache_key]
                if (now - cached_time) < self._COMPANY_CACHE_TTL:
                    return cached_articles[:limit]

            # Build search queries
            queries = [f"{ticker} stock"]
            clean_name = None
            if company_name and company_name != ticker:
                # Strip common suffixes for cleaner search
                clean_name = re.sub(
                    r'\s+(Inc\.?|Corp\.?|Ltd\.?|plc|PLC|Co\.|Company|Group|Holdings|Incorporated|Corporation|International|Enterprises)\s*$',
                    '', company_name)
                clean_name = clean_name.strip(' &,')
                if clean_name and clean_name.lower() != ticker.lower():
                    queries.append(f"{clean_name} company")

            # Fetch all search queries in parallel
            async def _fetch_query(query: str) -> list[dict]:
                url = (
                    f"https://news.google.com/rss/search?"
                    f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
                )
                feed_config = {
                    "default_source": "Google News",
                    "has_source_tag": True,
                }
                xml = await asyncio.to_thread(_fetch_url_sync, url)
                if xml is None:
                    return []
                return _parse_single_feed(xml, feed_config)

            results = await asyncio.gather(
                *[_fetch_query(q) for q in queries],
                return_exceptions=True,
            )

            all_articles: list[dict] = []
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Company news search failed: %s", result)
                    continue
                all_articles.extend(result)

            # Deduplicate by URL
            seen_urls: set[str] = set()
            unique: list[dict] = []
            for a in all_articles:
                url = a.get("link", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    _classify_article(a)
                    unique.append(a)

            # Title-key dedup (catch same article with different redirect URLs)
            seen_titles: set[str] = set()
            title_deduped: list[dict] = []
            for a in unique:
                tk = _title_key(a.get("title", ""))
                if tk and tk not in seen_titles:
                    seen_titles.add(tk)
                    title_deduped.append(a)
                elif not tk:
                    title_deduped.append(a)
            unique = title_deduped

            # Relevance filter — keep only articles mentioning the ticker or company
            if company_name:
                clean_name_lower = clean_name.lower() if clean_name else ""
            else:
                clean_name_lower = ""
            ticker_lower = ticker.lower()

            relevant = []
            for a in unique:
                text = f"{a.get('title', '')} {a.get('snippet', '')}".lower()
                if ticker_lower in text or (clean_name_lower and clean_name_lower in text):
                    relevant.append(a)
            unique = relevant if relevant else unique  # fallback to all if filter is too aggressive

            # Sort newest first
            def sort_key(article: dict) -> float:
                pub = article.get("published")
                if not pub:
                    return 0.0
                try:
                    dt = datetime.fromisoformat(pub)
                    return dt.timestamp()
                except Exception:
                    return 0.0

            unique.sort(key=sort_key, reverse=True)

            # Cache result
            self._company_cache[cache_key] = (now, unique)

            logger.info("Fetched %d company news articles for %s (%d queries)",
                         len(unique), ticker, len(queries))

            return unique[:limit]
