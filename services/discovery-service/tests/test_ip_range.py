"""
Tests for IP range utility module.
"""

import ipaddress
import pytest

from app.utils.ip_range import (
    IPRangeParseError,
    detect_ip_range_format,
    format_ip_range_for_scanner,
    get_hosts_from_range,
    parse_ip_range,
    validate_ip_range,
    _range_to_cidr,
)


class TestParseIPRange:
    """Test parse_ip_range function."""

    def test_valid_cidr_class_c(self):
        """Test parsing /24 CIDR notation."""
        result, count = parse_ip_range("192.168.1.0/24")
        assert result == "192.168.1.0/24"
        assert count == 254  # Usable hosts (256 - 2)

    def test_valid_cidr_class_b(self):
        """Test parsing /16 CIDR notation."""
        result, count = parse_ip_range("172.16.0.0/16")
        assert result == "172.16.0.0/16"
        assert count == 65534  # Usable hosts (65536 - 2)

    def test_valid_cidr_single_ip(self):
        """Test parsing /32 CIDR notation (single IP)."""
        result, count = parse_ip_range("192.168.1.1/32")
        assert result == "192.168.1.1/32"
        assert count == 1

    def test_valid_cidr_31(self):
        """Test parsing /31 CIDR notation (point-to-point)."""
        result, count = parse_ip_range("192.168.1.0/31")
        assert result == "192.168.1.0/31"
        # /31 has no network/broadcast distinction per RFC 3021
        assert count == 2

    def test_valid_cidr_large(self):
        """Test parsing /8 CIDR notation."""
        result, count = parse_ip_range("10.0.0.0/8")
        assert result == "10.0.0.0/8"
        assert count == 16777214  # Very large network

    def test_valid_ip_range_small(self):
        """Test parsing small IP range."""
        result, count = parse_ip_range("192.168.1.1-192.168.1.10")
        assert result == "192.168.1.1-192.168.1.10"
        assert count == 10

    def test_valid_ip_range_large(self):
        """Test parsing large IP range."""
        result, count = parse_ip_range("10.0.0.1-10.0.0.254")
        assert result == "10.0.0.1-10.0.0.254"
        assert count == 254

    def test_valid_ip_range_single(self):
        """Test parsing single IP in range format."""
        result, count = parse_ip_range("192.168.1.5-192.168.1.5")
        assert result == "192.168.1.5/32"  # Should convert to CIDR
        assert count == 1

    def test_valid_single_ip(self):
        """Test parsing single IP (no range)."""
        result, count = parse_ip_range("192.168.1.1")
        assert result == "192.168.1.1/32"
        assert count == 1

    def test_single_ip_edge_cases(self):
        """Test single IPs at boundaries."""
        # First IP in range
        result, count = parse_ip_range("0.0.0.0")
        assert result == "0.0.0.0/32"
        assert count == 1

        # Last IP in range
        result, count = parse_ip_range("255.255.255.255")
        assert result == "255.255.255.255/32"
        assert count == 1

    def test_ip_range_converts_to_cidr_when_possible(self):
        """Test that ranges matching CIDR boundaries are converted."""
        # This range is exactly a /24 network
        result, count = parse_ip_range("192.168.1.0-192.168.1.255")
        assert result == "192.168.1.0/24"
        assert count == 254

    def test_invalid_cidr_bad_prefix(self):
        """Test invalid CIDR with bad prefix."""
        with pytest.raises(IPRangeParseError) as exc_info:
            parse_ip_range("192.168.1.0/33")
        assert "Invalid CIDR notation" in str(exc_info.value)

    def test_invalid_cidr_bad_ip(self):
        """Test invalid CIDR with bad IP."""
        with pytest.raises(IPRangeParseError) as exc_info:
            parse_ip_range("256.168.1.0/24")
        assert "Invalid CIDR notation" in str(exc_info.value)

    def test_invalid_range_reversed(self):
        """Test IP range with start > end."""
        with pytest.raises(IPRangeParseError) as exc_info:
            parse_ip_range("192.168.1.100-192.168.1.1")
        assert "Start IP must be less than or equal to end IP" in str(exc_info.value)

    def test_invalid_range_bad_ip(self):
        """Test IP range with invalid IP."""
        with pytest.raises(IPRangeParseError) as exc_info:
            parse_ip_range("192.168.1.1-256.168.1.100")
        assert "Invalid IP range" in str(exc_info.value)

    def test_invalid_single_ip(self):
        """Test invalid single IP."""
        with pytest.raises(IPRangeParseError) as exc_info:
            parse_ip_range("256.168.1.1")
        assert "Invalid IP address" in str(exc_info.value)

    def test_invalid_format_gibberish(self):
        """Test completely invalid format."""
        with pytest.raises(IPRangeParseError) as exc_info:
            parse_ip_range("not-an-ip")
        assert "Invalid IP address" in str(exc_info.value)

    def test_whitespace_handling(self):
        """Test that whitespace is trimmed."""
        result, count = parse_ip_range("  192.168.1.0/24  ")
        assert result == "192.168.1.0/24"
        assert count == 254


class TestGetHostsFromRange:
    """Test get_hosts_from_range function."""

    def test_get_hosts_from_cidr(self):
        """Test getting hosts from CIDR."""
        hosts = get_hosts_from_range("192.168.1.0/30")
        assert len(hosts) == 2  # .1 and .2 (network and broadcast excluded)
        assert str(hosts[0]) == "192.168.1.1"
        assert str(hosts[1]) == "192.168.1.2"

    def test_get_hosts_from_range(self):
        """Test getting hosts from range notation."""
        hosts = get_hosts_from_range("192.168.1.10-192.168.1.15")
        assert len(hosts) == 6
        assert str(hosts[0]) == "192.168.1.10"
        assert str(hosts[-1]) == "192.168.1.15"

    def test_get_hosts_from_single_ip(self):
        """Test getting hosts from single IP."""
        hosts = get_hosts_from_range("192.168.1.1/32")
        assert len(hosts) == 1
        assert str(hosts[0]) == "192.168.1.1"

    def test_get_hosts_cross_octet_boundary(self):
        """Test getting hosts that cross octet boundary."""
        hosts = get_hosts_from_range("192.168.0.250-192.168.1.5")
        assert len(hosts) == 12
        assert str(hosts[0]) == "192.168.0.250"
        assert str(hosts[-1]) == "192.168.1.5"


class TestValidateIPRange:
    """Test validate_ip_range function."""

    def test_valid_range_under_limit(self):
        """Test valid range under max size."""
        result, count = validate_ip_range("192.168.1.0/24", max_size=65536)
        assert result == "192.168.1.0/24"
        assert count == 254

    def test_range_exceeds_max_size(self):
        """Test range that exceeds max size."""
        with pytest.raises(IPRangeParseError) as exc_info:
            validate_ip_range("10.0.0.0/8", max_size=1000)
        assert "too large" in str(exc_info.value)
        assert "16777214" in str(exc_info.value)  # The actual count

    def test_empty_network(self):
        """Test network with 0 usable hosts."""
        # /31 has 2 addresses but they're usable per RFC 3021
        # So we test with a range that has 0 hosts
        with pytest.raises(IPRangeParseError) as exc_info:
            validate_ip_range("192.168.1.5-192.168.1.4", max_size=65536)
        assert "Start IP must be less than or equal to end IP" in str(exc_info.value)

    def test_valid_single_ip(self):
        """Test single IP validation."""
        result, count = validate_ip_range("192.168.1.1", max_size=65536)
        assert result == "192.168.1.1/32"
        assert count == 1

    def test_max_size_boundary(self):
        """Test exactly at max size boundary."""
        # /16 has 65534 usable hosts (under 65536 limit)
        result, count = validate_ip_range("172.16.0.0/16", max_size=65536)
        assert count == 65534
        assert result == "172.16.0.0/16"


class TestFormatIPRangeForScanner:
    """Test format_ip_range_for_scanner function."""

    def test_python_scanner_format(self):
        """Test formatting for Python scanner."""
        result = format_ip_range_for_scanner("192.168.1.0/24", "python")
        assert result == "192.168.1.0/24"

    def test_nmap_scanner_format_cidr(self):
        """Test Nmap formatting with CIDR."""
        result = format_ip_range_for_scanner("192.168.1.0/24", "nmap")
        assert result == "192.168.1.0/24"

    def test_nmap_scanner_format_range(self):
        """Test Nmap formatting with range."""
        result = format_ip_range_for_scanner("192.168.1.1-192.168.1.100", "nmap")
        # Nmap supports range notation directly
        assert result == "192.168.1.1-192.168.1.100"

    def test_masscan_scanner_format_cidr(self):
        """Test Masscan formatting with CIDR."""
        result = format_ip_range_for_scanner("192.168.1.0/24", "masscan")
        assert result == "192.168.1.0/24"

    def test_masscan_scanner_format_small_range(self):
        """Test Masscan formatting with small range (converted to comma-separated)."""
        result = format_ip_range_for_scanner("192.168.1.1-192.168.1.5", "masscan")
        # Small ranges are converted to comma-separated IPs
        assert result == "192.168.1.1,192.168.1.2,192.168.1.3,192.168.1.4,192.168.1.5"

    def test_masscan_scanner_format_large_range(self):
        """Test Masscan formatting with large range (kept as range)."""
        result = format_ip_range_for_scanner("192.168.1.1-192.168.1.2000", "masscan")
        # Large ranges stay as-is (would be too many IPs)
        assert result == "192.168.1.1-192.168.1.2000"

    def test_default_scanner_format(self):
        """Test formatting with unknown scanner type defaults to python."""
        result = format_ip_range_for_scanner("192.168.1.0/24", "unknown")
        assert result == "192.168.1.0/24"


class TestDetectIPRangeFormat:
    """Test detect_ip_range_format function."""

    def test_detect_cidr(self):
        """Test detecting CIDR format."""
        assert detect_ip_range_format("192.168.1.0/24") == "cidr"
        assert detect_ip_range_format("10.0.0.0/8") == "cidr"
        assert detect_ip_range_format("172.16.0.0/16") == "cidr"

    def test_detect_range(self):
        """Test detecting range format."""
        assert detect_ip_range_format("192.168.1.1-192.168.1.100") == "range"
        assert detect_ip_range_format("10.0.0.1-10.0.0.254") == "range"

    def test_detect_single_ip(self):
        """Test detecting single IP format."""
        assert detect_ip_range_format("192.168.1.1") == "single"
        assert detect_ip_range_format("10.0.0.1") == "single"

    def test_detect_invalid(self):
        """Test detecting invalid formats."""
        assert detect_ip_range_format("not-an-ip") == "invalid"
        assert detect_ip_range_format("256.168.1.0/24") == "invalid"
        assert detect_ip_range_format("") == "invalid"

    def test_detect_whitespace(self):
        """Test that whitespace doesn't affect detection."""
        assert detect_ip_range_format("  192.168.1.0/24  ") == "cidr"
        assert detect_ip_range_format("  192.168.1.1-192.168.1.10  ") == "range"


class TestRangeToCidr:
    """Test _range_to_cidr helper function."""

    def test_exact_cidr_match(self):
        """Test range that exactly matches CIDR."""
        start = ipaddress.ip_address("192.168.1.0")
        end = ipaddress.ip_address("192.168.1.255")
        result = _range_to_cidr(start, end)
        assert result == "192.168.1.0/24"

    def test_partial_match_returns_none(self):
        """Test range that doesn't match any CIDR."""
        start = ipaddress.ip_address("192.168.1.5")
        end = ipaddress.ip_address("192.168.1.100")
        result = _range_to_cidr(start, end)
        assert result is None

    def test_single_ip_returns_32(self):
        """Test single IP returns /32."""
        start = ipaddress.ip_address("192.168.1.1")
        end = ipaddress.ip_address("192.168.1.1")
        result = _range_to_cidr(start, end)
        assert result == "192.168.1.1/32"

    def test_small_range_returns_none(self):
        """Test small non-CIDR-aligned range."""
        start = ipaddress.ip_address("192.168.1.0")
        end = ipaddress.ip_address("192.168.1.127")
        result = _range_to_cidr(start, end)
        # This is half a /24, not a valid CIDR
        assert result is None


class TestIPRangeIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_cidr(self):
        """Test full workflow with CIDR input."""
        input_range = "192.168.1.0/24"

        # Step 1: Detect format
        fmt = detect_ip_range_format(input_range)
        assert fmt == "cidr"

        # Step 2: Parse and validate
        normalized, count = validate_ip_range(input_range, max_size=65536)
        assert normalized == "192.168.1.0/24"
        assert count == 254

        # Step 3: Get hosts
        hosts = get_hosts_from_range(normalized)
        assert len(hosts) == 254

        # Step 4: Format for scanners
        python_fmt = format_ip_range_for_scanner(normalized, "python")
        nmap_fmt = format_ip_range_for_scanner(normalized, "nmap")
        masscan_fmt = format_ip_range_for_scanner(normalized, "masscan")

        assert python_fmt == "192.168.1.0/24"
        assert nmap_fmt == "192.168.1.0/24"
        assert masscan_fmt == "192.168.1.0/24"

    def test_full_workflow_range(self):
        """Test full workflow with range input."""
        input_range = "192.168.1.10-192.168.1.20"

        # Step 1: Detect format
        fmt = detect_ip_range_format(input_range)
        assert fmt == "range"

        # Step 2: Parse and validate
        normalized, count = validate_ip_range(input_range, max_size=65536)
        assert normalized == "192.168.1.10-192.168.1.20"
        assert count == 11

        # Step 3: Get hosts
        hosts = get_hosts_from_range(normalized)
        assert len(hosts) == 11
        assert str(hosts[0]) == "192.168.1.10"
        assert str(hosts[-1]) == "192.168.1.20"

    def test_full_workflow_single_ip(self):
        """Test full workflow with single IP input."""
        input_range = "192.168.1.50"

        # Step 1: Detect format
        fmt = detect_ip_range_format(input_range)
        assert fmt == "single"

        # Step 2: Parse and validate
        normalized, count = validate_ip_range(input_range, max_size=65536)
        assert normalized == "192.168.1.50/32"
        assert count == 1

        # Step 3: Get hosts
        hosts = get_hosts_from_range(normalized)
        assert len(hosts) == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_class_a_network(self):
        """Test Class A network (/8)."""
        result, count = parse_ip_range("10.0.0.0/8")
        assert count == 16777214

    def test_class_b_network(self):
        """Test Class B network (/16)."""
        result, count = parse_ip_range("172.16.0.0/16")
        assert count == 65534

    def test_class_c_network(self):
        """Test Class C network (/24)."""
        result, count = parse_ip_range("192.168.1.0/24")
        assert count == 254

    def test_loopback_range(self):
        """Test loopback range."""
        result, count = parse_ip_range("127.0.0.1")
        assert result == "127.0.0.1/32"
        assert count == 1

    def test_multicast_range(self):
        """Test multicast range."""
        result, count = parse_ip_range("224.0.0.0/24")
        assert result == "224.0.0.0/24"

    def test_range_across_octets(self):
        """Test range that crosses octet boundaries."""
        result, count = parse_ip_range("192.168.0.250-192.168.1.5")
        assert count == 12
        hosts = get_hosts_from_range(result)
        assert len(hosts) == 12

    def test_very_small_range(self):
        """Test very small range of 2 IPs."""
        result, count = parse_ip_range("192.168.1.1-192.168.1.2")
        assert count == 2
        hosts = get_hosts_from_range(result)
        assert len(hosts) == 2


class TestPerformanceEdgeCases:
    """Test performance with large ranges."""

    def test_large_range_list_generation(self):
        """Test that large ranges don't cause memory issues."""
        # /16 network - should be manageable
        hosts = get_hosts_from_range("172.16.0.0/16")
        assert len(hosts) == 65534
        # Just check first and last
        assert str(hosts[0]) == "172.16.0.1"
        assert str(hosts[-1]) == "172.16.255.254"

    def test_masscan_format_large_range(self):
        """Test that large ranges for masscan don't expand to list."""
        # Large range should stay as-is, not expand to comma-separated
        result = format_ip_range_for_scanner("10.0.0.1-10.0.0.1000", "masscan")
        assert result == "10.0.0.1-10.0.0.1000"
        assert "," not in result


# Fixtures for common test data
@pytest.fixture
def valid_cidrs():
    """Fixture providing various valid CIDR notations."""
    return [
        "192.168.1.0/24",
        "10.0.0.0/8",
        "172.16.0.0/16",
        "192.168.1.1/32",
        "0.0.0.0/0",
    ]


@pytest.fixture
def valid_ranges():
    """Fixture providing various valid IP ranges."""
    return [
        "192.168.1.1-192.168.1.100",
        "10.0.0.1-10.0.0.254",
        "172.16.0.1-172.16.0.10",
    ]


@pytest.fixture
def valid_single_ips():
    """Fixture providing valid single IPs."""
    return [
        "192.168.1.1",
        "10.0.0.1",
        "0.0.0.0",
        "255.255.255.255",
    ]


class TestWithFixtures:
    """Tests using fixtures."""

    def test_all_cidrs_valid(self, valid_cidrs):
        """Test all fixture CIDRs are valid."""
        for cidr in valid_cidrs:
            assert detect_ip_range_format(cidr) == "cidr"
            result, count = parse_ip_range(cidr)
            assert count > 0

    def test_all_ranges_valid(self, valid_ranges):
        """Test all fixture ranges are valid."""
        for range_str in valid_ranges:
            assert detect_ip_range_format(range_str) == "range"
            result, count = parse_ip_range(range_str)
            assert count > 0

    def test_all_single_ips_valid(self, valid_single_ips):
        """Test all fixture single IPs are valid."""
        for ip in valid_single_ips:
            assert detect_ip_range_format(ip) == "single"
            result, count = parse_ip_range(ip)
            assert count == 1
