"""Network call interceptor for Startup-Auditor scrapers.

Captures and classifies network requests made during page load:
- URL deduplication and validation
- Service classification (LLM, API, social, analytics, CDN, cloud)
- Wafer Pass LLM detection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class NetworkCall:
    """Represents a single network call.

    Attributes:
        url: The full URL requested
        domain: The domain extracted from the URL
        service_type: Classification type (llm, api, social, etc.)
        service_name: Human-readable service name
    """
    url: str
    domain: str = ""
    service_type: str = "unknown"
    service_name: str = "Unknown"

    def __post_init__(self):
        if not self.domain:
            self.domain = extract_domain(self.url)


# Known services dictionary for classification
KNOWN_SERVICES: Dict[str, Dict[str, str]] = {
    "api.wafer.ai": {"type": "llm", "name": "Wafer Pass"},
    "wafer.ai": {"type": "llm", "name": "Wafer Pass"},
    "api.github.com": {"type": "api", "name": "GitHub"},
    "github.com": {"type": "api", "name": "GitHub"},
    "linkedin.com": {"type": "social", "name": "LinkedIn"},
    "www.linkedin.com": {"type": "social", "name": "LinkedIn"},
    "crunchbase.com": {"type": "data", "name": "Crunchbase"},
    "www.crunchbase.com": {"type": "data", "name": "Crunchbase"},
    "google-analytics.com": {"type": "analytics", "name": "Google Analytics"},
    "www.google-analytics.com": {"type": "analytics", "name": "Google Analytics"},
    "cloudflare.com": {"type": "cdn", "name": "Cloudflare"},
    "cdnjs.cloudflare.com": {"type": "cdn", "name": "Cloudflare CDN"},
    "aws.amazon.com": {"type": "cloud", "name": "AWS"},
    "amazonaws.com": {"type": "cloud", "name": "AWS"},
    "fonts.googleapis.com": {"type": "cdn", "name": "Google Fonts"},
    "fonts.gstatic.com": {"type": "cdn", "name": "Google Fonts"},
    "stripe.com": {"type": "api", "name": "Stripe"},
    "api.stripe.com": {"type": "api", "name": "Stripe"},
}


def extract_domain(url: str) -> str:
    """Extract domain from a URL.

    Args:
        url: Full URL string

    Returns:
        Domain name (e.g., "api.github.com" from "https://api.github.com/users")
    """
    try:
        parsed = urlparse(url)
        # Handle data: and other non-HTTP schemes
        if not parsed.netloc and parsed.scheme not in ("http", "https"):
            return ""
        domain = parsed.netloc or parsed.path.split("/")[0]
        # Remove port if present
        domain = domain.split(":")[0]
        return domain
    except Exception:
        return ""


def classify_service(domain: str) -> tuple[str, str]:
    """Classify a domain into a service type and name.

    Args:
        domain: Domain name to classify

    Returns:
        Tuple of (service_type, service_name)
    """
    # Check exact match first
    if domain in KNOWN_SERVICES:
        service = KNOWN_SERVICES[domain]
        return service["type"], service["name"]

    # Check if domain ends with known service domain
    for known_domain, service in KNOWN_SERVICES.items():
        if domain.endswith(known_domain) or domain.endswith("." + known_domain):
            return service["type"], service["name"]

    # Default classification
    return "unknown", "Unknown"


def detect_wafer_pass(network_calls: List[NetworkCall]) -> tuple[bool, float]:
    """Detect if Wafer Pass LLM is used based on network calls.

    Args:
        network_calls: List of captured network calls

    Returns:
        Tuple of (is_detected, confidence_score)
    """
    for call in network_calls:
        if call.service_type == "llm" and "Wafer" in call.service_name:
            return True, 0.9

        # Also check for wafer.ai domain in any form
        if "wafer.ai" in call.domain:
            return True, 0.7

    return False, 0.0


class NetworkInterceptor:
    """Intercepts and classifies network requests during page load.

    Features:
    - Request/response logging
    - URL deduplication
    - Service classification
    - Wafer Pass detection

    Usage with Playwright:
        interceptor = NetworkInterceptor()
        page.on("request", interceptor.on_request)
        page.on("response", interceptor.on_response)
        await page.goto(url)
        network_calls = interceptor.get_network_calls()
    """

    def __init__(self) -> None:
        """Initialize network interceptor."""
        self._requests: Dict[str, str] = {}  # request_id -> url
        self._responses: Dict[str, dict] = {}  # request_id -> response info
        self._network_calls: List[NetworkCall] = []

    def on_request(self, request) -> None:
        """Handle page request event.

        Args:
            request: Playwright request object
        """
        url = request.url
        request_id = request.route or id(request)

        # Only track HTTP requests (not data:, about:, etc.)
        if url.startswith(("http://", "https://")):
            self._requests[request_id] = url

    def on_response(self, response) -> None:
        """Handle page response event.

        Args:
            response: Playwright response object
        """
        request_id = response.request.route if hasattr(response.request, 'route') else id(response.request)
        url = response.url

        # Store response info
        self._responses[request_id] = {
            "url": url,
            "status": response.status,
            "headers": dict(response.headers) if hasattr(response, 'headers') else {},
        }

    def finalize(self) -> None:
        """Process collected requests/responses into network calls.

        Call this after page load is complete.
        """
        seen_urls = set()

        # Match requests with responses
        for request_id, url in self._requests.items():
            # Deduplicate
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Get response info if available
            response_info = self._responses.get(request_id, {})
            status = response_info.get("status", 0)

            # Only include successful responses (optional filter)
            # For now, include all to detect all services

            # Extract domain and classify
            domain = extract_domain(url)
            service_type, service_name = classify_service(domain)

            # Create network call
            call = NetworkCall(
                url=url,
                domain=domain,
                service_type=service_type,
                service_name=service_name,
            )
            self._network_calls.append(call)

    def get_network_calls(self) -> List[NetworkCall]:
        """Get list of captured network calls.

        Returns:
            List of NetworkCall objects
        """
        return self._network_calls

    def get_network_services(self) -> Dict[str, List[str]]:
        """Get classified services grouped by type.

        Returns:
            Dictionary mapping service type to list of service names
        """
        services: Dict[str, List[str]] = {}
        for call in self._network_calls:
            if call.service_type not in services:
                services[call.service_type] = []
            if call.service_name not in services[call.service_type]:
                services[call.service_type].append(call.service_name)
        return services

    def clear(self) -> None:
        """Clear all captured network data."""
        self._requests.clear()
        self._responses.clear()
        self._network_calls.clear()
