"""
IP range parsing utilities for discovery service.
Supports three formats:
1. CIDR notation (e.g., 192.168.1.0/24)
2. IP range (e.g., 192.168.1.1-192.168.1.100)
3. Single IP (e.g., 192.168.1.1)
"""

import ipaddress
import re
from typing import List, Tuple


class IPRangeParseError(Exception):
    """Raised when IP range parsing fails."""

    pass


def parse_ip_range(ip_range: str) -> Tuple[str, int]:
    """
    Parse IP range in various formats and return normalized CIDR notation.

    Args:
        ip_range: IP range in one of three formats:
            - CIDR: 192.168.1.0/24
            - Range: 192.168.1.1-192.168.1.100
            - Single IP: 192.168.1.1

    Returns:
        Tuple of (normalized_cidr_or_list, host_count)
        For ranges that can't be expressed as CIDR, returns comma-separated IP list

    Raises:
        IPRangeParseError: If the format is invalid

    Examples:
        >>> parse_ip_range("192.168.1.0/24")
        ("192.168.1.0/24", 254)

        >>> parse_ip_range("192.168.1.1-192.168.1.10")
        ("192.168.1.1-192.168.1.10", 10)

        >>> parse_ip_range("192.168.1.5")
        ("192.168.1.5/32", 1)
    """
    ip_range = ip_range.strip()

    # Try CIDR notation first
    if "/" in ip_range:
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            # Calculate usable hosts (exclude network and broadcast addresses)
            host_count = network.num_addresses - 2
            if host_count < 0:
                host_count = network.num_addresses  # For /31 and /32
            return (str(network), host_count)
        except ValueError as e:
            raise IPRangeParseError(f"Invalid CIDR notation: {e}")

    # Try IP range notation (start-end)
    if "-" in ip_range:
        try:
            start_ip, end_ip = ip_range.split("-", 1)
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()

            # Validate both IPs
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)

            # Ensure start <= end
            if int(start) > int(end):
                raise IPRangeParseError("Start IP must be less than or equal to end IP")

            # Calculate host count
            host_count = int(end) - int(start) + 1

            # Check if range can be expressed as CIDR
            cidr = _range_to_cidr(start, end)
            if cidr:
                return (cidr, host_count)
            else:
                # Return as range notation for scanners to handle
                return (f"{start_ip}-{end_ip}", host_count)

        except ValueError as e:
            raise IPRangeParseError(f"Invalid IP range: {e}")

    # Try single IP
    try:
        ip = ipaddress.ip_address(ip_range)
        return (f"{ip}/32", 1)
    except ValueError:
        raise IPRangeParseError(f"Invalid IP address: {ip_range}")


def _range_to_cidr(start: ipaddress.IPv4Address, end: ipaddress.IPv4Address) -> str:
    """
    Try to convert an IP range to CIDR notation.
    Returns CIDR string if possible, None otherwise.
    """
    start_int = int(start)
    end_int = int(end)

    # Try to find a CIDR that covers exactly this range
    for prefix_len in range(32, -1, -1):
        network = ipaddress.ip_network(f"{start}/{prefix_len}", strict=False)
        network_start = int(network.network_address)
        network_end = int(network.broadcast_address)

        if network_start == start_int and network_end == end_int:
            return str(network)

    return None


def get_hosts_from_range(ip_range: str) -> List[ipaddress.IPv4Address]:
    """
    Get list of all host IP addresses from a range string.

    Args:
        ip_range: IP range in CIDR, range, or single IP format

    Returns:
        List of IPv4Address objects
    """
    normalized, _ = parse_ip_range(ip_range)

    # CIDR notation
    if "/" in normalized:
        network = ipaddress.ip_network(normalized, strict=False)
        return list(network.hosts())

    # Range notation
    if "-" in normalized:
        start_ip, end_ip = normalized.split("-", 1)
        start = int(ipaddress.ip_address(start_ip.strip()))
        end = int(ipaddress.ip_address(end_ip.strip()))
        return [ipaddress.ip_address(i) for i in range(start, end + 1)]

    # Single IP (shouldn't happen as parse_ip_range converts to /32)
    return [ipaddress.ip_address(normalized.replace("/32", ""))]


def validate_ip_range(ip_range: str, max_size: int = 65536) -> Tuple[str, int]:
    """
    Validate and parse IP range with size limit.

    Args:
        ip_range: IP range string
        max_size: Maximum number of hosts allowed

    Returns:
        Tuple of (normalized_range, host_count)

    Raises:
        IPRangeParseError: If invalid or too large
    """
    try:
        normalized, host_count = parse_ip_range(ip_range)

        if host_count > max_size:
            raise IPRangeParseError(
                f"IP range too large: {host_count} hosts (max: {max_size})"
            )

        if host_count == 0:
            raise IPRangeParseError("IP range contains no valid hosts")

        return normalized, host_count

    except IPRangeParseError:
        raise
    except Exception as e:
        raise IPRangeParseError(f"Invalid IP range: {e}")


def format_ip_range_for_scanner(ip_range: str, scanner_type: str = "python") -> str:
    """
    Format IP range for specific scanner compatibility.

    Different scanners support different formats:
    - Python: Supports all formats
    - Masscan: Supports CIDR and comma-separated IPs
    - Nmap: Supports all formats plus comma-separated

    Args:
        ip_range: IP range in any supported format
        scanner_type: Type of scanner

    Returns:
        Formatted string for the scanner
    """
    normalized, _ = parse_ip_range(ip_range)

    if scanner_type == "masscan":
        # Masscan supports CIDR and comma-separated IPs
        # For ranges, we need to convert to comma-separated
        if "-" in normalized:
            hosts = get_hosts_from_range(normalized)
            # For large ranges, this could be huge, so truncate with warning
            if len(hosts) > 1000:
                # Just use the range notation and let masscan handle it
                return normalized
            return ",".join(str(h) for h in hosts)
        return normalized

    elif scanner_type == "nmap":
        # Nmap supports CIDR, ranges with hyphen, comma-separated
        # Range notation is already compatible
        return normalized

    else:  # python or default
        # Python scanner uses the normalized format
        return normalized


# Regex patterns for validation
CIDR_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"/(?:3[0-2]|[1-2]?[0-9])$"
)

IP_RANGE_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"-"
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

SINGLE_IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def detect_ip_range_format(ip_range: str) -> str:
    """
    Detect the format of an IP range string.

    Returns:
        'cidr', 'range', 'single', or 'invalid'
    """
    ip_range = ip_range.strip()

    if "/" in ip_range:
        if CIDR_PATTERN.match(ip_range):
            return "cidr"
        return "invalid"

    if "-" in ip_range:
        if IP_RANGE_PATTERN.match(ip_range):
            return "range"
        return "invalid"

    if SINGLE_IP_PATTERN.match(ip_range):
        return "single"

    return "invalid"
