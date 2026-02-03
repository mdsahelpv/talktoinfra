"""
Prometheus metrics configuration for Discovery Service.

Provides custom metrics for:
- Scan operations (duration, counts, status)
- Host discovery and management
- Health checks
- Scanner availability
"""

import time
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
from prometheus_client.core import CollectorRegistry


# Scan duration histogram - tracks scan time by type
scan_duration_histogram = Histogram(
    "scan_duration_seconds",
    "Scan duration in seconds",
    ["scan_type"],
    buckets=[
        0.1,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
        300.0,
        600.0,
        1800.0,
        3600.0,
    ],
)

# Scan counter - tracks total scans by type and status
scan_counter = Counter(
    "scans_total",
    "Total number of scans",
    ["scan_type", "status"],
)

# Host discovery counter
hosts_discovered_total = Counter(
    "hosts_discovered_total",
    "Total number of hosts discovered",
    ["scan_type"],
)

# Managed hosts gauge
hosts_managed_total = Gauge(
    "hosts_managed_total",
    "Total number of managed hosts",
    ["status"],
)

# Total managed hosts (all statuses)
total_managed_hosts = Gauge(
    "total_managed_hosts",
    "Total number of managed hosts across all statuses",
)

# Port scan counter
ports_scanned_total = Counter(
    "ports_scanned_total",
    "Total number of ports scanned",
    ["scanner"],
)

# Open ports discovered
ports_open_total = Counter(
    "ports_open_total",
    "Total number of open ports discovered",
    ["scanner"],
)

# Health check counter
health_check_counter = Counter(
    "health_checks_total",
    "Total number of health checks performed",
    ["status"],
)

# Active scans gauge
active_scans = Gauge(
    "active_scans",
    "Number of currently running scans",
    ["scan_type"],
)

# Scanner availability gauge
scanner_availability = Gauge(
    "scanner_availability",
    "Scanner binary availability (1=available, 0=unavailable)",
    ["scanner"],
)

# Job lifecycle metrics
job_created_counter = Counter(
    "jobs_created_total",
    "Total number of scan jobs created",
    ["scan_type"],
)

job_status_counter = Counter(
    "jobs_status_total",
    "Total number of job status changes",
    ["from_status", "to_status"],
)

# HTTP metrics (created via middleware)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

# Error tracking
error_counter = Counter(
    "errors_total",
    "Total number of errors",
    ["error_type", "component"],
)


@contextmanager
def track_scan_duration(scan_type: str) -> Generator[None, None, None]:
    """Context manager to track scan duration.

    Usage:
        with track_scan_duration("nmap"):
            await scanner.start_scan(...)
    """
    start_time = time.time()
    active_scans.labels(scan_type=scan_type).inc()
    try:
        yield
    finally:
        duration = time.time() - start_time
        scan_duration_histogram.labels(scan_type=scan_type).observe(duration)
        active_scans.labels(scan_type=scan_type).dec()


def record_scan_completion(scan_type: str, status: str, hosts_found: int = 0) -> None:
    """Record a scan completion with metrics.

    Args:
        scan_type: Type of scan (nmap, masscan, python, hybrid)
        status: Completion status (completed, failed, cancelled)
        hosts_found: Number of hosts discovered
    """
    scan_counter.labels(scan_type=scan_type, status=status).inc()

    if hosts_found > 0:
        hosts_discovered_total.labels(scan_type=scan_type).inc(hosts_found)


def record_ports_scanned(scanner: str, ports_count: int, open_count: int = 0) -> None:
    """Record port scanning metrics.

    Args:
        scanner: Scanner name
        ports_count: Total ports scanned
        open_count: Number of open ports found
    """
    ports_scanned_total.labels(scanner=scanner).inc(ports_count)
    if open_count > 0:
        ports_open_total.labels(scanner=scanner).inc(open_count)


def record_health_check(status: str) -> None:
    """Record a health check result.

    Args:
        status: Health check result (online, offline, error)
    """
    health_check_counter.labels(status=status).inc()


def update_scanner_availability(scanner: str, available: bool) -> None:
    """Update scanner availability metric.

    Args:
        scanner: Scanner name (nmap, masscan, python)
        available: True if scanner is available
    """
    scanner_availability.labels(scanner=scanner).set(1.0 if available else 0.0)


def record_job_created(scan_type: str) -> None:
    """Record job creation.

    Args:
        scan_type: Type of scan
    """
    job_created_counter.labels(scan_type=scan_type).inc()


def record_job_status_change(from_status: str, to_status: str) -> None:
    """Record job status transition.

    Args:
        from_status: Previous status
        to_status: New status
    """
    job_status_counter.labels(from_status=from_status, to_status=to_status).inc()


def record_error(error_type: str, component: str) -> None:
    """Record an error occurrence.

    Args:
        error_type: Type of error
        component: Component where error occurred
    """
    error_counter.labels(error_type=error_type, component=component).inc()


def update_managed_hosts_count(status_counts: dict) -> None:
    """Update managed hosts gauge with current counts.

    Args:
        status_counts: Dict with status -> count mappings
    """
    total = 0
    for status, count in status_counts.items():
        if status != "total":
            hosts_managed_total.labels(status=status).set(count)
            total += count
    total_managed_hosts.set(total)


def get_metrics() -> bytes:
    """Generate Prometheus metrics output.

    Returns:
        Metrics in Prometheus exposition format
    """
    return generate_latest(REGISTRY)


def get_registry() -> CollectorRegistry:
    """Get the Prometheus registry.

    Returns:
        The global Prometheus registry
    """
    return REGISTRY


# Create metrics object that wraps all functions and variables for easy import
class MetricsWrapper:
    """Wrapper class to provide unified metrics interface."""

    # Metric counters/gauges/histograms
    http_requests_total = http_requests_total
    http_request_duration_seconds = http_request_duration_seconds
    http_response_size_bytes = http_response_size_bytes
    scan_duration_histogram = scan_duration_histogram
    scan_counter = scan_counter
    hosts_discovered_total = hosts_discovered_total
    hosts_managed_total = hosts_managed_total
    total_managed_hosts = total_managed_hosts
    ports_scanned_total = ports_scanned_total
    ports_open_total = ports_open_total
    health_check_counter = health_check_counter
    active_scans = active_scans
    scanner_availability = scanner_availability
    job_created_counter = job_created_counter
    job_status_counter = job_status_counter
    error_counter = error_counter

    # Functions
    track_scan_duration = staticmethod(track_scan_duration)
    record_scan_completion = staticmethod(record_scan_completion)
    record_ports_scanned = staticmethod(record_ports_scanned)
    record_health_check = staticmethod(record_health_check)
    update_scanner_availability = staticmethod(update_scanner_availability)
    record_job_created = staticmethod(record_job_created)
    record_job_status_change = staticmethod(record_job_status_change)
    record_error = staticmethod(record_error)
    update_managed_hosts_count = staticmethod(update_managed_hosts_count)
    get_metrics = staticmethod(get_metrics)
    get_registry = staticmethod(get_registry)


# Create singleton instance for import
metrics = MetricsWrapper()
