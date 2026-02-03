"""
Unit tests for ScannerFactory.
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from app.scanners.base import BaseScanner
from app.scanners.factory import ScannerFactory
from app.scanners.masscan import MasscanScanner
from app.scanners.nmap import NmapScanner
from app.scanners.python_async import PythonAsyncScanner


class TestScannerCreation:
    """Test scanner instance creation."""

    def test_create_python_scanner(self) -> None:
        """Test creating Python async scanner."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.masscan_rate = 1000
            mock_settings.masscan_adapter = None
            mock_settings.masscan_wait_time = 10
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_settings.nmap_timing_template = "T4"
            mock_settings.nmap_service_detection = True
            mock_settings.nmap_os_detection = False
            mock_settings.nmap_script_scan = False
            mock_settings.python_scan_timeout = 2.0
            mock_settings.python_scan_concurrent = 50
            mock_get_settings.return_value = mock_settings

            scanner = ScannerFactory.create_scanner("python")

        assert isinstance(scanner, PythonAsyncScanner)
        assert scanner.name == "python"

    def test_create_fast_scanner(self) -> None:
        """Test creating fast scanner (masscan)."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.masscan_rate = 1000
            mock_settings.masscan_adapter = None
            mock_settings.masscan_wait_time = 10
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_settings.nmap_timing_template = "T4"
            mock_settings.nmap_service_detection = True
            mock_settings.nmap_os_detection = False
            mock_settings.nmap_script_scan = False
            mock_settings.python_scan_timeout = 2.0
            mock_settings.python_scan_concurrent = 50
            mock_get_settings.return_value = mock_settings

            scanner = ScannerFactory.create_scanner("fast")

        assert isinstance(scanner, MasscanScanner)
        assert scanner.name == "masscan"

    def test_create_detailed_scanner(self) -> None:
        """Test creating detailed scanner (nmap)."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.masscan_rate = 1000
            mock_settings.masscan_adapter = None
            mock_settings.masscan_wait_time = 10
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_settings.nmap_timing_template = "T4"
            mock_settings.nmap_service_detection = True
            mock_settings.nmap_os_detection = False
            mock_settings.nmap_script_scan = False
            mock_settings.python_scan_timeout = 2.0
            mock_settings.python_scan_concurrent = 50
            mock_get_settings.return_value = mock_settings

            scanner = ScannerFactory.create_scanner("detailed")

        assert isinstance(scanner, NmapScanner)
        assert scanner.name == "nmap"

    def test_create_hybrid_scanner(self) -> None:
        """Test creating hybrid scanner (returns masscan)."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.masscan_rate = 1000
            mock_settings.masscan_adapter = None
            mock_settings.masscan_wait_time = 10
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_settings.nmap_timing_template = "T4"
            mock_settings.nmap_service_detection = True
            mock_settings.nmap_os_detection = False
            mock_settings.nmap_script_scan = False
            mock_settings.python_scan_timeout = 2.0
            mock_settings.python_scan_concurrent = 50
            mock_get_settings.return_value = mock_settings

            scanner = ScannerFactory.create_scanner("hybrid")

        assert isinstance(scanner, MasscanScanner)
        assert scanner.name == "masscan"

    def test_create_unknown_scanner_raises_error(self) -> None:
        """Test that unknown scanner type raises ValueError."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_get_settings.return_value = mock_settings

            with pytest.raises(ValueError) as exc_info:
                ScannerFactory.create_scanner("unknown")

        assert "Unknown scanner type" in str(exc_info.value)
        assert "unknown" in str(exc_info.value)

    def test_scanner_configuration_passed(self) -> None:
        """Test that scanner receives correct configuration."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/custom/masscan"
            mock_settings.masscan_rate = 5000
            mock_settings.masscan_adapter = "eth1"
            mock_settings.masscan_wait_time = 30
            mock_settings.nmap_path = "/custom/nmap"
            mock_settings.nmap_timing_template = "T5"
            mock_settings.nmap_service_detection = False
            mock_settings.nmap_os_detection = True
            mock_settings.nmap_script_scan = True
            mock_settings.python_scan_timeout = 5.0
            mock_settings.python_scan_concurrent = 100
            mock_get_settings.return_value = mock_settings

            masscan = ScannerFactory.create_scanner("fast")
            assert masscan.binary_path == "/custom/masscan"
            assert masscan.rate == 5000
            assert masscan.adapter == "eth1"
            assert masscan.wait_time == 30

            nmap = ScannerFactory.create_scanner("detailed")
            assert nmap.binary_path == "/custom/nmap"
            assert nmap.timing_template == "T5"
            assert nmap.service_detection is False
            assert nmap.os_detection is True
            assert nmap.script_scan is True


class TestAvailableScanners:
    """Test getting available scanners list."""

    def test_get_available_scanners_structure(self) -> None:
        """Test structure of available scanners list."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch(
                "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
            ):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        assert isinstance(scanners, list)
        assert len(scanners) == 4  # python, fast, detailed, hybrid

        # Check required fields for each scanner
        for scanner in scanners:
            assert "name" in scanner
            assert "description" in scanner
            assert "available" in scanner
            assert "requires_root" in scanner
            assert "recommended_for" in scanner
            assert "average_speed" in scanner

    def test_python_scanner_always_available(self) -> None:
        """Test that Python scanner is always marked available."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.masscan.shutil.which", return_value=None):
                with patch("app.scanners.nmap.shutil.which", return_value=None):
                    scanners = ScannerFactory.get_available_scanners()

        python_scanner = next(s for s in scanners if s["name"] == "python")
        assert python_scanner["available"] is True

    def test_masscan_availability_check(self) -> None:
        """Test that masscan availability is checked correctly."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch(
                "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
            ):
                with patch("app.scanners.nmap.shutil.which", return_value=None):
                    scanners = ScannerFactory.get_available_scanners()

        masscan_scanner = next(s for s in scanners if s["name"] == "fast")
        assert masscan_scanner["available"] is True
        assert masscan_scanner["requires_root"] is True

    def test_masscan_not_available(self) -> None:
        """Test masscan marked as unavailable when binary missing."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.masscan.shutil.which", return_value=None):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        masscan_scanner = next(s for s in scanners if s["name"] == "fast")
        assert masscan_scanner["available"] is False

    def test_nmap_availability_check(self) -> None:
        """Test that nmap availability is checked correctly."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.masscan.shutil.which", return_value=None):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        nmap_scanner = next(s for s in scanners if s["name"] == "detailed")
        assert nmap_scanner["available"] is True
        assert nmap_scanner["requires_root"] is False

    def test_hybrid_availability_both_tools(self) -> None:
        """Test hybrid scanner available when both tools present."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch(
                "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
            ):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        hybrid_scanner = next(s for s in scanners if s["name"] == "hybrid")
        assert hybrid_scanner["available"] is True

    def test_hybrid_not_available_missing_masscan(self) -> None:
        """Test hybrid scanner not available when masscan missing."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.masscan.shutil.which", return_value=None):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        hybrid_scanner = next(s for s in scanners if s["name"] == "hybrid")
        assert hybrid_scanner["available"] is False

    def test_hybrid_not_available_missing_nmap(self) -> None:
        """Test hybrid scanner not available when nmap missing."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch(
                "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
            ):
                with patch("app.scanners.nmap.shutil.which", return_value=None):
                    scanners = ScannerFactory.get_available_scanners()

        hybrid_scanner = next(s for s in scanners if s["name"] == "hybrid")
        assert hybrid_scanner["available"] is False


class TestScannerRecommendation:
    """Test scanner recommendation logic."""

    def test_recommend_python_for_small_networks(self) -> None:
        """Test Python scanner recommended for small networks."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which", return_value=None):
                recommendation = ScannerFactory.recommend_scanner(
                    10, need_details=False
                )

        assert recommendation == "python"

    def test_recommend_detailed_for_small_networks_with_details(self) -> None:
        """Test detailed scanner for small networks when details needed."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which") as mock_which:

                def which_side_effect(path):
                    if path == "/usr/bin/nmap":
                        return "/usr/bin/nmap"
                    return None

                mock_which.side_effect = which_side_effect

                recommendation = ScannerFactory.recommend_scanner(10, need_details=True)

        assert recommendation == "detailed"

    def test_recommend_fast_for_large_networks(self) -> None:
        """Test fast scanner recommended for large networks."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which") as mock_which:

                def which_side_effect(path):
                    if path == "/usr/bin/masscan":
                        return "/usr/bin/masscan"
                    return None

                mock_which.side_effect = which_side_effect

                recommendation = ScannerFactory.recommend_scanner(
                    2000, need_details=False
                )

        assert recommendation == "fast"

    def test_recommend_python_when_masscan_not_available(self) -> None:
        """Test Python scanner when masscan not available for large networks."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which", return_value=None):
                recommendation = ScannerFactory.recommend_scanner(
                    2000, need_details=False
                )

        assert recommendation == "python"

    def test_recommend_hybrid_for_medium_networks(self) -> None:
        """Test hybrid scanner for medium networks when both tools available."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which") as mock_which:

                def which_side_effect(path):
                    if path in ["/usr/bin/masscan", "/usr/bin/nmap"]:
                        return path
                    return None

                mock_which.side_effect = which_side_effect

                recommendation = ScannerFactory.recommend_scanner(
                    500, need_details=True
                )

        assert recommendation == "hybrid"

    def test_recommend_fast_for_medium_networks_no_details(self) -> None:
        """Test fast scanner for medium networks when details not needed."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which") as mock_which:

                def which_side_effect(path):
                    if path in ["/usr/bin/masscan", "/usr/bin/nmap"]:
                        return path
                    return None

                mock_which.side_effect = which_side_effect

                recommendation = ScannerFactory.recommend_scanner(
                    500, need_details=False
                )

        assert recommendation == "fast"

    def test_recommend_fast_for_medium_networks_no_nmap(self) -> None:
        """Test fast scanner when nmap not available but masscan is."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which") as mock_which:

                def which_side_effect(path):
                    if path == "/usr/bin/masscan":
                        return "/usr/bin/masscan"
                    return None

                mock_which.side_effect = which_side_effect

                recommendation = ScannerFactory.recommend_scanner(
                    500, need_details=True
                )

        assert recommendation == "fast"

    def test_recommend_python_for_medium_networks_no_tools(self) -> None:
        """Test Python scanner when no external tools available."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which", return_value=None):
                recommendation = ScannerFactory.recommend_scanner(
                    500, need_details=True
                )

        assert recommendation == "python"

    def test_threshold_boundaries(self) -> None:
        """Test recommendation at network size boundaries."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.factory.shutil.which") as mock_which:

                def which_side_effect(path):
                    if path in ["/usr/bin/masscan", "/usr/bin/nmap"]:
                        return path
                    return None

                mock_which.side_effect = which_side_effect

                # Small network (<=100)
                assert (
                    ScannerFactory.recommend_scanner(50, need_details=True)
                    == "detailed"
                )
                assert (
                    ScannerFactory.recommend_scanner(100, need_details=True)
                    == "detailed"
                )

                # Medium network (100-1000)
                assert (
                    ScannerFactory.recommend_scanner(101, need_details=True) == "hybrid"
                )
                assert (
                    ScannerFactory.recommend_scanner(500, need_details=True) == "hybrid"
                )
                assert (
                    ScannerFactory.recommend_scanner(1000, need_details=True)
                    == "hybrid"
                )

                # Large network (>1000)
                assert (
                    ScannerFactory.recommend_scanner(1001, need_details=True) == "fast"
                )
                assert (
                    ScannerFactory.recommend_scanner(10000, need_details=True) == "fast"
                )


class TestScannerDescriptions:
    """Test scanner descriptions in available scanners."""

    def test_python_scanner_description(self) -> None:
        """Test Python scanner has appropriate description."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.masscan.shutil.which", return_value=None):
                with patch("app.scanners.nmap.shutil.which", return_value=None):
                    scanners = ScannerFactory.get_available_scanners()

        python_scanner = next(s for s in scanners if s["name"] == "python")
        assert (
            "external" in python_scanner["recommended_for"].lower()
            or "no external" in python_scanner["recommended_for"].lower()
        )
        assert (
            "50-100" in python_scanner["average_speed"]
            or "hosts/sec" in python_scanner["average_speed"]
        )

    def test_fast_scanner_description(self) -> None:
        """Test fast (masscan) scanner has appropriate description."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch(
                "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
            ):
                with patch("app.scanners.nmap.shutil.which", return_value=None):
                    scanners = ScannerFactory.get_available_scanners()

        fast_scanner = next(s for s in scanners if s["name"] == "fast")
        assert (
            "large" in fast_scanner["recommended_for"].lower()
            or "fast" in fast_scanner["recommended_for"].lower()
        )
        assert (
            "1000" in fast_scanner["average_speed"]
            or "hosts/sec" in fast_scanner["average_speed"]
        )

    def test_detailed_scanner_description(self) -> None:
        """Test detailed (nmap) scanner has appropriate description."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch("app.scanners.masscan.shutil.which", return_value=None):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        detailed_scanner = next(s for s in scanners if s["name"] == "detailed")
        assert (
            "detailed" in detailed_scanner["recommended_for"].lower()
            or "service" in detailed_scanner["recommended_for"].lower()
        )
        assert (
            "10-50" in detailed_scanner["average_speed"]
            or "hosts/sec" in detailed_scanner["average_speed"]
        )

    def test_hybrid_scanner_description(self) -> None:
        """Test hybrid scanner has appropriate description."""
        with patch("app.scanners.factory.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.masscan_path = "/usr/bin/masscan"
            mock_settings.nmap_path = "/usr/bin/nmap"
            mock_get_settings.return_value = mock_settings

            with patch(
                "app.scanners.masscan.shutil.which", return_value="/usr/bin/masscan"
            ):
                with patch(
                    "app.scanners.nmap.shutil.which", return_value="/usr/bin/nmap"
                ):
                    scanners = ScannerFactory.get_available_scanners()

        hybrid_scanner = next(s for s in scanners if s["name"] == "hybrid")
        assert (
            "best" in hybrid_scanner["description"].lower()
            or "both" in hybrid_scanner["description"].lower()
        )
        assert (
            "production" in hybrid_scanner["recommended_for"].lower()
            or "recommended" in hybrid_scanner["recommended_for"].lower()
        )
