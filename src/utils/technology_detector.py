"""Technology detection utilities for Common Crawl MCP Server.

This module detects technologies, frameworks, CMS, analytics, and other tools
used by websites based on HTML patterns, meta tags, scripts, and comments.
"""

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Technology detection patterns database
TECHNOLOGY_PATTERNS = {
    "cms": {
        "WordPress": {
            "patterns": [
                r"wp-content/",
                r"wp-includes/",
                r"/wp-json/",
            ],
            "meta": ["generator"],
            "meta_content": ["WordPress"],
            "confidence_base": 0.9
        },
        "Drupal": {
            "patterns": [
                r"Drupal\.settings",
                r"/sites/default/files/",
                r"drupal\.js",
            ],
            "meta": ["generator"],
            "meta_content": ["Drupal"],
            "confidence_base": 0.9
        },
        "Joomla": {
            "patterns": [
                r"/components/com_",
                r"Joomla!",
                r"/media/jui/",
            ],
            "meta": ["generator"],
            "meta_content": ["Joomla"],
            "confidence_base": 0.9
        },
        "Wix": {
            "patterns": [
                r"wix\.com",
                r"_wix",
                r"parastorage",
            ],
            "confidence_base": 0.95
        },
        "Squarespace": {
            "patterns": [
                r"squarespace",
                r"sqsp",
            ],
            "confidence_base": 0.95
        },
        "Shopify": {
            "patterns": [
                r"cdn\.shopify\.com",
                r"Shopify\.theme",
                r"shopify-features",
            ],
            "confidence_base": 0.95
        },
        "Webflow": {
            "patterns": [
                r"webflow\.com",
                r"webflow\.js",
            ],
            "confidence_base": 0.95
        },
    },
    "frameworks": {
        "React": {
            "patterns": [
                r"react(?:-dom)?\.(?:production|development)\.min\.js",
                r"__REACT",
                r"data-reactroot",
                r"data-reactid",
            ],
            "confidence_base": 0.85
        },
        "Vue.js": {
            "patterns": [
                r"vue(?:\.min)?\.js",
                r"__VUE__",
                r"v-(?:if|for|bind|on|model)",
            ],
            "confidence_base": 0.85
        },
        "Angular": {
            "patterns": [
                r"ng-(?:app|controller|model|view)",
                r"angular(?:\.min)?\.js",
                r"\[ng-",
            ],
            "confidence_base": 0.85
        },
        "Next.js": {
            "patterns": [
                r"_next/",
                r"__NEXT_DATA__",
                r"next\.js",
            ],
            "confidence_base": 0.9
        },
        "Nuxt.js": {
            "patterns": [
                r"_nuxt/",
                r"__NUXT__",
            ],
            "confidence_base": 0.9
        },
        "Svelte": {
            "patterns": [
                r"svelte",
                r"__svelte",
            ],
            "confidence_base": 0.85
        },
        "jQuery": {
            "patterns": [
                r"jquery(?:-\d+\.\d+\.\d+)?(?:\.min)?\.js",
                r"\$\(document\)\.ready",
            ],
            "confidence_base": 0.7
        },
    },
    "analytics": {
        "Google Analytics": {
            "patterns": [
                r"google-analytics\.com/(?:ga|analytics)\.js",
                r"gtag\(",
                r"UA-\d+-\d+",
                r"G-[A-Z0-9]+",
            ],
            "confidence_base": 0.95
        },
        "Google Tag Manager": {
            "patterns": [
                r"googletagmanager\.com/gtm\.js",
                r"GTM-[A-Z0-9]+",
            ],
            "confidence_base": 0.95
        },
        "Mixpanel": {
            "patterns": [
                r"mixpanel\.com/libs/mixpanel",
                r"mixpanel\.init",
            ],
            "confidence_base": 0.95
        },
        "Segment": {
            "patterns": [
                r"cdn\.segment\.com",
                r"analytics\.load",
            ],
            "confidence_base": 0.95
        },
        "Amplitude": {
            "patterns": [
                r"amplitude\.com",
                r"amplitude\.getInstance",
            ],
            "confidence_base": 0.95
        },
        "Hotjar": {
            "patterns": [
                r"hotjar\.com",
                r"_hjSettings",
            ],
            "confidence_base": 0.95
        },
    },
    "cdn": {
        "Cloudflare": {
            "headers": ["cf-ray", "cf-cache-status"],
            "patterns": [
                r"cloudflare",
                r"cdnjs\.cloudflare\.com",
            ],
            "confidence_base": 0.9
        },
        "Fastly": {
            "headers": ["x-fastly-request-id"],
            "patterns": [r"fastly"],
            "confidence_base": 0.9
        },
        "Akamai": {
            "headers": ["x-akamai"],
            "patterns": [r"akamai"],
            "confidence_base": 0.9
        },
        "Amazon CloudFront": {
            "headers": ["x-amz-cf-id", "via"],
            "patterns": [r"cloudfront\.net"],
            "confidence_base": 0.9
        },
    },
    "hosting": {
        "AWS": {
            "patterns": [
                r"amazonaws\.com",
                r"\.aws\.",
            ],
            "confidence_base": 0.8
        },
        "Vercel": {
            "headers": ["x-vercel-id"],
            "patterns": [
                r"vercel\.app",
                r"\.vercel\.com",
            ],
            "confidence_base": 0.9
        },
        "Netlify": {
            "headers": ["x-nf-request-id"],
            "patterns": [
                r"netlify\.app",
                r"\.netlify\.com",
            ],
            "confidence_base": 0.9
        },
        "GitHub Pages": {
            "patterns": [
                r"github\.io",
                r"pages\.github\.com",
            ],
            "confidence_base": 0.95
        },
        "Heroku": {
            "patterns": [
                r"herokuapp\.com",
            ],
            "confidence_base": 0.95
        },
    },
    "advertising": {
        "Google Ads": {
            "patterns": [
                r"googleadservices\.com",
                r"googlesyndication\.com",
                r"adsbygoogle",
            ],
            "confidence_base": 0.95
        },
        "Facebook Pixel": {
            "patterns": [
                r"facebook\.net/.*?/fbevents\.js",
                r"fbq\(",
            ],
            "confidence_base": 0.95
        },
        "DoubleClick": {
            "patterns": [
                r"doubleclick\.net",
            ],
            "confidence_base": 0.95
        },
    },
    "security": {
        "reCAPTCHA": {
            "patterns": [
                r"google\.com/recaptcha",
                r"grecaptcha",
            ],
            "confidence_base": 0.95
        },
        "Cloudflare Turnstile": {
            "patterns": [
                r"challenges\.cloudflare\.com",
                r"turnstile",
            ],
            "confidence_base": 0.95
        },
    },
}


class TechnologyDetector:
    """Detect technologies used by websites."""

    def __init__(self):
        """Initialize technology detector."""
        self.patterns = TECHNOLOGY_PATTERNS

    def detect(
        self,
        html: str,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Detect technologies from HTML and headers.

        Args:
            html: HTML content
            headers: HTTP response headers

        Returns:
            Dictionary with detected technologies and confidence scores

        Example:
            >>> detector = TechnologyDetector()
            >>> result = detector.detect(html, headers)
            >>> result['detected']['React']
            {'category': 'frameworks', 'confidence': 0.85, 'version': None}
        """
        detected = {}

        # Check each category
        for category, technologies in self.patterns.items():
            for tech_name, tech_patterns in technologies.items():
                confidence = self._check_technology(
                    html,
                    headers or {},
                    tech_patterns
                )

                if confidence > 0:
                    detected[tech_name] = {
                        "category": category,
                        "confidence": confidence,
                        "version": self._detect_version(html, tech_name),
                    }

        # Sort by confidence
        detected = dict(
            sorted(
                detected.items(),
                key=lambda x: x[1]["confidence"],
                reverse=True
            )
        )

        return {
            "detected": detected,
            "count": len(detected),
            "categories": self._group_by_category(detected),
        }

    def _check_technology(
        self,
        html: str,
        headers: dict[str, str],
        patterns: dict[str, Any],
    ) -> float:
        """Check if technology is present based on patterns.

        Args:
            html: HTML content
            headers: HTTP headers
            patterns: Technology pattern definition

        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.0
        base_confidence = patterns.get("confidence_base", 0.8)

        # Check HTML patterns
        if "patterns" in patterns:
            for pattern in patterns["patterns"]:
                if re.search(pattern, html, re.IGNORECASE):
                    confidence = base_confidence
                    break

        # Check meta tags
        if "meta" in patterns:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            for meta_name in patterns["meta"]:
                meta_tag = soup.find("meta", attrs={"name": meta_name})
                if meta_tag and meta_tag.get("content"):
                    content = meta_tag.get("content", "")

                    # Check if content matches expected values
                    if "meta_content" in patterns:
                        for expected in patterns["meta_content"]:
                            if expected.lower() in content.lower():
                                confidence = base_confidence
                                break
                    else:
                        confidence = base_confidence

        # Check headers
        if "headers" in patterns:
            for header_name in patterns["headers"]:
                if header_name.lower() in [h.lower() for h in headers.keys()]:
                    confidence = base_confidence
                    break

        return confidence

    def _detect_version(self, html: str, tech_name: str) -> Optional[str]:
        """Attempt to detect technology version.

        Args:
            html: HTML content
            tech_name: Technology name

        Returns:
            Version string or None
        """
        version_patterns = {
            "WordPress": r"WordPress\s+([\d.]+)",
            "React": r"react(?:-dom)?[/@]([\d.]+)",
            "Vue.js": r"vue[/@]([\d.]+)",
            "Angular": r"angular[/@]([\d.]+)",
            "jQuery": r"jquery[/-]([\d.]+)",
        }

        if tech_name in version_patterns:
            match = re.search(version_patterns[tech_name], html, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _group_by_category(self, detected: dict) -> dict[str, list[str]]:
        """Group detected technologies by category.

        Args:
            detected: Detected technologies dictionary

        Returns:
            Dictionary mapping category to list of technology names
        """
        categories = {}

        for tech_name, info in detected.items():
            category = info["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(tech_name)

        return categories

    def get_tech_stack_summary(self, detected: dict) -> dict[str, Any]:
        """Generate a human-readable tech stack summary.

        Args:
            detected: Output from detect() method

        Returns:
            Structured summary of technology stack
        """
        summary = {
            "total_technologies": detected["count"],
            "categories": {},
            "primary_stack": [],
        }

        # Group by category with details
        for tech_name, info in detected["detected"].items():
            category = info["category"]

            if category not in summary["categories"]:
                summary["categories"][category] = []

            tech_info = {
                "name": tech_name,
                "confidence": info["confidence"],
                "version": info["version"],
            }

            summary["categories"][category].append(tech_info)

            # High-confidence primary stack
            if info["confidence"] >= 0.85:
                summary["primary_stack"].append(tech_name)

        return summary
