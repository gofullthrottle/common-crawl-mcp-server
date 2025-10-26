# Common Crawl MCP Server

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> Transform Common Crawl's petabyte-scale web archive into an accessible research platform through AI-powered analysis.

## 🚀 Features

An **epic MCP server** that enables:

- **Discovery & Metadata** - Explore available crawls, search the index, analyze domain statistics
- **Data Fetching** - Retrieve page content efficiently with smart caching
- **Parsing & Analysis** - Extract structured data, detect technologies, analyze SEO
- **Aggregation & Statistics** - Domain-wide reports, link graphs, evolution timelines
- **Export & Integration** - CSV, JSONL, custom datasets, report generation
- **MCP Resources** - LLM-accessible data exposure
- **MCP Prompts** - Guided workflows for complex analysis

## 📋 Prerequisites

- Python 3.11+
- AWS CLI (optional - for custom S3 configurations)
- Redis (optional - for enhanced caching)

## 🔧 Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/common-crawl-mcp-server.git
cd common-crawl-mcp-server

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Development Setup

```bash
# Install with development dependencies
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

## 💻 Usage

### Starting the Server

```bash
# Run with stdio transport (for MCP clients)
python -m src.server

# Or use the installed command
common-crawl-mcp
```

### Configuration

Create a `.env` file in the project root:

```env
# Cache Configuration
CACHE_DIR=./cache
CACHE_MAX_SIZE_GB=50

# S3 Configuration (uses anonymous access by default)
AWS_REGION=us-east-1

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379

# Rate Limiting
MAX_CONCURRENT_REQUESTS=5
REQUESTS_PER_SECOND=10
```

### Example Usage with MCP

```python
# Using the MCP client
from mcp import ClientSession

async with ClientSession() as session:
    # List available crawls
    crawls = await session.call_tool("list_crawls")

    # Search for a domain
    results = await session.call_tool("search_index", {
        "query": "example.com",
        "crawl_id": "CC-MAIN-2024-10"
    })

    # Fetch page content
    page = await session.call_tool("fetch_page_content", {
        "url": "https://example.com",
        "crawl_id": "CC-MAIN-2024-10"
    })
```

## 🏗️ Architecture

```
src/
├── server.py              # Main FastMCP server
├── config.py              # Configuration management
├── core/                  # Core infrastructure
│   ├── cc_client.py       # CDX Server API client
│   ├── cache.py           # Multi-tier caching
│   ├── s3_manager.py      # S3 access wrapper
│   └── warc_parser.py     # WARC file parsing
├── tools/                 # MCP tools
│   ├── discovery.py       # Discovery & metadata
│   ├── fetching.py        # Data fetching
│   ├── parsing.py         # Parsing & analysis
│   ├── aggregation.py     # Aggregation & statistics
│   ├── export.py          # Export & integration
│   └── advanced.py        # Advanced features
├── resources/             # MCP resources
├── prompts/               # MCP prompts
├── models/                # Pydantic models
└── utils/                 # Utilities
```

## 🔍 Available Tools

### Discovery & Metadata
- `list_crawls()` - Get all available Common Crawl crawls
- `get_crawl_stats(crawl_id)` - Statistics for specific crawl
- `search_index(query, crawl_id)` - Search the CDX index
- `get_domain_stats(domain, crawl_id)` - Domain statistics
- `compare_crawls(crawl_ids, domain)` - Track changes over time

### Data Fetching
- `fetch_page_content(url, crawl_id)` - Get page HTML and metadata
- `fetch_warc_records(urls, crawl_id)` - Batch fetch WARC records
- `batch_fetch_pages(domain, crawl_id)` - Get all pages from domain

### Parsing & Analysis
- `parse_html(content)` - Extract structured data from HTML
- `analyze_technologies(url, crawl_id)` - Detect tech stack
- `extract_links(url, crawl_id)` - Link analysis
- `analyze_seo(url, crawl_id)` - SEO audit
- `detect_language(url, crawl_id)` - Language detection

### Aggregation & Statistics
- `domain_technology_report(domain, crawl_id)` - Complete tech audit
- `domain_link_graph(domain, crawl_id)` - Internal link structure
- `keyword_frequency_analysis(urls, keywords)` - Keyword analysis
- `header_analysis(domain, crawl_id)` - HTTP header analysis

### Export & Integration
- `export_to_csv(data, fields, filepath)` - CSV export
- `export_to_jsonl(data, filepath)` - JSONL export
- `create_dataset(query, name)` - Save reusable datasets
- `generate_report(analysis_results, format)` - Generate reports

## 📚 MCP Resources

Access Common Crawl data through MCP resources:

- `commoncrawl://crawls` - List of all crawls
- `commoncrawl://crawl/{crawl_id}/stats` - Crawl statistics
- `commoncrawl://domain/{domain}/latest` - Latest domain data
- `commoncrawl://domain/{domain}/timeline` - Historical presence
- `commoncrawl://page/{url}` - Page content from latest crawl

## 🎯 MCP Prompts

Guided workflows for complex analysis:

- `investigate_domain(domain)` - Comprehensive domain investigation
- `competitive_analysis(domains)` - Multi-domain comparison
- `technology_audit(domain)` - Technology stack deep dive
- `seo_audit(url)` - SEO analysis workflow
- `historical_investigation(domain, start_date, end_date)` - Temporal analysis

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_core/test_cc_client.py

# Run integration tests
pytest tests/integration/
```

## 📊 Use Cases

### SEO Professional
> "Show me all pages from competitor.com in the last 6 crawls, analyze their title tag patterns, and identify their most linked-to content"

### Security Researcher
> "Find all WordPress sites from the latest crawl using outdated jQuery versions, export the domains to CSV"

### Data Scientist
> "Get 10,000 news articles from .com domains, extract structured data, export to JSONL for training"

### Business Analyst
> "Compare mycompany.com vs competitor1.com vs competitor2.com - technology usage, page count trends, link authority over the past 2 years"

## 🚦 Performance

- **Complete technology report** for a domain in <2 minutes
- **Cache reduces S3 costs** by >80%
- **Test coverage** >80%
- **API response times** <500ms (cached), <5s (uncached)

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- Uses [Common Crawl](https://commoncrawl.org/) public dataset
- WARC parsing by [warcio](https://github.com/webrecorder/warcio)
- HTML parsing by [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)

## 📚 Resources

- [Common Crawl Documentation](https://commoncrawl.org/the-data/get-started/)
- [CDX Server API](https://index.commoncrawl.org/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Implementation Plan](.claude/plans/2025-10-25-common-crawl-mcp-server.md)

---

**Status:** 🚧 In Development
**Started:** 2025-10-25
**Target Completion:** 2025-11-15

[![ClickUp](https://img.shields.io/badge/ClickUp-Project-7B68EE)](https://app.clickup.com/90144358408)
