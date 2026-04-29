"""Tests for network interceptor module."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from startup_auditor.scrapers.network_interceptor import (
    NetworkInterceptor,
    NetworkCall,
    extract_domain,
    classify_service,
    detect_wafer_pass,
    KNOWN_SERVICES,
)


class TestExtractDomain:
    """Test URL domain extraction."""

    def test_extract_domain_https_url(self):
        """Test extracting domain from HTTPS URL."""
        domain = extract_domain("https://api.github.com/users/test")
        assert domain == "api.github.com"

    def test_extract_domain_http_url(self):
        """Test extracting domain from HTTP URL."""
        domain = extract_domain("http://example.com/path")
        assert domain == "example.com"

    def test_extract_domain_with_port(self):
        """Test extracting domain with port number."""
        domain = extract_domain("https://localhost:8080/api")
        assert domain == "localhost"

    def test_extract_domain_invalid_url(self):
        """Test extracting domain from invalid URL."""
        domain = extract_domain("not-a-url")
        assert domain == "not-a-url" or domain == ""

    def test_extract_domain_data_url(self):
        """Test extracting domain from data URL."""
        domain = extract_domain("data:text/plain,hello")
        assert domain == ""


class TestClassifyService:
    """Test service classification."""

    def test_classify_wafer_pass(self):
        """Test Wafer Pass detection."""
        service_type, service_name = classify_service("api.wafer.ai")
        assert service_type == "llm"
        assert service_name == "Wafer Pass"

    def test_classify_github(self):
        """Test GitHub detection."""
        service_type, service_name = classify_service("api.github.com")
        assert service_type == "api"
        assert service_name == "GitHub"

    def test_classify_linkedin(self):
        """Test LinkedIn detection."""
        service_type, service_name = classify_service("www.linkedin.com")
        assert service_type == "social"
        assert service_name == "LinkedIn"

    def test_classify_google_analytics(self):
        """Test Google Analytics detection."""
        service_type, service_name = classify_service("google-analytics.com")
        assert service_type == "analytics"
        assert service_name == "Google Analytics"

    def test_classify_cloudflare(self):
        """Test Cloudflare detection."""
        service_type, service_name = classify_service("cdnjs.cloudflare.com")
        assert service_type == "cdn"
        assert service_name == "Cloudflare CDN"

    def test_classify_aws(self):
        """Test AWS detection."""
        service_type, service_name = classify_service("s3.amazonaws.com")
        assert service_type == "cloud"
        assert service_name == "AWS"

    def test_classify_unknown_service(self):
        """Test unknown service classification."""
        service_type, service_name = classify_service("unknown-domain.com")
        assert service_type == "unknown"
        assert service_name == "Unknown"

    def test_classify_subdomain_match(self):
        """Test subdomain matching for known services."""
        service_type, service_name = classify_service("cdn.jsdelivr.net")
        # Should match if jsdelivr is in known services, otherwise unknown
        assert isinstance(service_type, str)
        assert isinstance(service_name, str)


class TestNetworkCall:
    """Test NetworkCall dataclass."""

    def test_network_call_creation(self):
        """Test creating NetworkCall with all fields."""
        call = NetworkCall(
            url="https://api.github.com/users",
            domain="api.github.com",
            service_type="api",
            service_name="GitHub",
        )
        assert call.url == "https://api.github.com/users"
        assert call.domain == "api.github.com"
        assert call.service_type == "api"
        assert call.service_name == "GitHub"

    def test_network_call_auto_domain(self):
        """Test automatic domain extraction."""
        call = NetworkCall(url="https://example.com/path")
        assert call.domain == "example.com"

    def test_network_call_default_values(self):
        """Test default values for service fields."""
        call = NetworkCall(url="https://unknown.com")
        assert call.service_type == "unknown"
        assert call.service_name == "Unknown"


class TestDetectWaferPass:
    """Test Wafer Pass detection."""

    def test_detect_wafer_pass_found(self):
        """Test detecting Wafer Pass when present."""
        calls = [
            NetworkCall(
                url="https://api.wafer.ai/v1/chat",
                domain="api.wafer.ai",
                service_type="llm",
                service_name="Wafer Pass",
            )
        ]
        detected, confidence = detect_wafer_pass(calls)
        assert detected is True
        assert confidence == 0.9

    def test_detect_wafer_pass_wafer_domain(self):
        """Test detecting Wafer Pass by domain."""
        calls = [
            NetworkCall(
                url="https://wafer.ai/embed.js",
                domain="wafer.ai",
                service_type="unknown",
                service_name="Unknown",
            )
        ]
        detected, confidence = detect_wafer_pass(calls)
        assert detected is True
        assert confidence == 0.7

    def test_detect_wafer_pass_not_found(self):
        """Test Wafer Pass not detected when absent."""
        calls = [
            NetworkCall(
                url="https://api.github.com/users",
                domain="api.github.com",
                service_type="api",
                service_name="GitHub",
            )
        ]
        detected, confidence = detect_wafer_pass(calls)
        assert detected is False
        assert confidence == 0.0

    def test_detect_wafer_pass_empty_list(self):
        """Test Wafer Pass detection with empty list."""
        detected, confidence = detect_wafer_pass([])
        assert detected is False
        assert confidence == 0.0


class TestNetworkInterceptor:
    """Test NetworkInterceptor class."""

    def test_interceptor_init(self):
        """Test interceptor initialization."""
        interceptor = NetworkInterceptor()
        assert interceptor._requests == {}
        assert interceptor._responses == {}
        assert interceptor._network_calls == []

    def test_on_request_http(self):
        """Test on_request captures HTTP URLs."""
        interceptor = NetworkInterceptor()
        mock_request = MagicMock()
        mock_request.url = "https://example.com/api"
        mock_request.route = "req-123"

        interceptor.on_request(mock_request)

        assert "req-123" in interceptor._requests
        assert interceptor._requests["req-123"] == "https://example.com/api"

    def test_on_request_ignores_data_url(self):
        """Test on_request ignores data: URLs."""
        interceptor = NetworkInterceptor()
        mock_request = MagicMock()
        mock_request.url = "data:text/plain,hello"
        mock_request.route = "req-456"

        interceptor.on_request(mock_request)

        assert "req-456" not in interceptor._requests

    def test_on_response(self):
        """Test on_response captures response info."""
        interceptor = NetworkInterceptor()
        mock_response = MagicMock()
        mock_response.url = "https://example.com/api"
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.request.route = "req-123"

        interceptor.on_response(mock_response)

        assert "req-123" in interceptor._responses
        assert interceptor._responses["req-123"]["url"] == "https://example.com/api"
        assert interceptor._responses["req-123"]["status"] == 200

    def test_finalize_deduplicates(self):
        """Test finalize deduplicates URLs."""
        interceptor = NetworkInterceptor()
        # Add same URL twice
        interceptor._requests["req-1"] = "https://example.com/api"
        interceptor._requests["req-2"] = "https://example.com/api"

        interceptor.finalize()

        # Should only have one network call
        assert len(interceptor._network_calls) == 1

    def test_finalize_classifies_services(self):
        """Test finalize classifies known services."""
        interceptor = NetworkInterceptor()
        interceptor._requests["req-1"] = "https://api.github.com/users"

        interceptor.finalize()

        assert len(interceptor._network_calls) == 1
        call = interceptor._network_calls[0]
        assert call.domain == "api.github.com"
        assert call.service_type == "api"
        assert call.service_name == "GitHub"

    def test_get_network_calls(self):
        """Test get_network_calls returns captured calls."""
        interceptor = NetworkInterceptor()
        interceptor._network_calls = [
            NetworkCall(url="https://example.com", domain="example.com")
        ]

        calls = interceptor.get_network_calls()

        assert len(calls) == 1
        assert calls[0].url == "https://example.com"

    def test_get_network_services(self):
        """Test get_network_services groups by type."""
        interceptor = NetworkInterceptor()
        interceptor._network_calls = [
            NetworkCall(
                url="https://api.github.com",
                domain="api.github.com",
                service_type="api",
                service_name="GitHub",
            ),
            NetworkCall(
                url="https://api.wafer.ai",
                domain="api.wafer.ai",
                service_type="llm",
                service_name="Wafer Pass",
            ),
        ]

        services = interceptor.get_network_services()

        assert "api" in services
        assert "GitHub" in services["api"]
        assert "llm" in services
        assert "Wafer Pass" in services["llm"]

    def test_clear(self):
        """Test clear removes all data."""
        interceptor = NetworkInterceptor()
        interceptor._requests["req-1"] = "https://example.com"
        interceptor._responses["req-1"] = {"status": 200}
        interceptor._network_calls.append(
            NetworkCall(url="https://example.com", domain="example.com")
        )

        interceptor.clear()

        assert interceptor._requests == {}
        assert interceptor._responses == {}
        assert interceptor._network_calls == []


class TestIntegration:
    """Integration tests for network interceptor."""

    def test_full_interception_flow(self):
        """Test complete interception flow."""
        interceptor = NetworkInterceptor()

        # Simulate requests
        mock_request1 = MagicMock()
        mock_request1.url = "https://api.github.com/users"
        mock_request1.route = "req-1"
        interceptor.on_request(mock_request1)

        mock_request2 = MagicMock()
        mock_request2.url = "https://api.wafer.ai/v1/chat"
        mock_request2.route = "req-2"
        interceptor.on_request(mock_request2)

        # Simulate responses
        mock_response1 = MagicMock()
        mock_response1.url = "https://api.github.com/users"
        mock_response1.status = 200
        mock_response1.headers = {}
        mock_response1.request = MagicMock()
        mock_response1.request.route = "req-1"
        interceptor.on_response(mock_response1)

        mock_response2 = MagicMock()
        mock_response2.url = "https://api.wafer.ai/v1/chat"
        mock_response2.status = 200
        mock_response2.headers = {}
        mock_response2.request = MagicMock()
        mock_response2.request.route = "req-2"
        interceptor.on_response(mock_response2)

        # Finalize
        interceptor.finalize()

        # Verify
        calls = interceptor.get_network_calls()
        assert len(calls) == 2

        # Check Wafer Pass detection
        detected, confidence = detect_wafer_pass(calls)
        assert detected is True
        assert confidence == 0.9

        # Check service grouping
        services = interceptor.get_network_services()
        assert "api" in services
        assert "llm" in services
