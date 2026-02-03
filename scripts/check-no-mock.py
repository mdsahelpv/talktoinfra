#!/usr/bin/env python3
"""
Check for mock data in production code.

This script scans the codebase for mock patterns that should not exist
in production code. It excludes test files and directories.

Usage:
    python scripts/check-no-mock.py

Exit codes:
    0 - No mock data found
    1 - Mock data detected in production code
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate mock data in production code
MOCK_PATTERNS = [
    # Function names
    r"_get_mock_resources\s*\(",
    r"get_mock_namespaces\s*\(",
    r"get_mock_pods\s*\(",
    r"get_mock_deployments\s*\(",
    r"get_mock_services\s*\(",
    r"get_mock_nodes\s*\(",
    r"create_mock_data\s*\(",
    r"generate_mock_resources\s*\(",
    
    # Variable names
    r"mock_data\s*=",
    r"MOCK_DATA\s*=",
    r"mock_resources\s*=",
    r"mock_response\s*=",
    r"MOCK_RESPONSE\s*=",
    
    # Testing utilities in production code
    r"from\s+unittest\.mock\s+import\s+MagicMock",
    r"from\s+unittest\.mock\s+import\s+Mock",
    r"from\s+unittest\.mock\s+import\s+patch",
    r"from\s+mock\s+import",
    r"MagicMock\s*\(",
    r"@patch\s*\(",
    r"@mock\.patch\s*\(",
    
    # Hardcoded test prefixes (excluding test files)
    r"\"test-[^\"]+\"",  # String literals with test- prefix
    r"'test-[^']+'",     # Single quote string literals with test- prefix
    
    # Mock data files
    r"mock_data\.json",
    r"mock_resources\.json",
    r"test_data\.json",
    
    # Common mock patterns
    r"mock_kubernetes",
    r"mock_k8s",
    r"fake_data",
    r"FAKE_DATA",
    r"dummy_data",
    r"DUMMY_DATA",
    r"stub_data",
    r"STUB_DATA",
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(pattern) for pattern in MOCK_PATTERNS]

# Directories and files to exclude
EXCLUDE_PATTERNS = [
    r"test_",
    r"_test\.py$",
    r"tests?/",
    r"__pycache__",
    r"\.pyc$",
    r"\.pytest_cache",
    r"\.git/",
    r"[\\/]venv[\\/]",  # Exclude venv directories anywhere in path
    r"[\\/]\.venv[\\/]",  # Exclude .venv directories
    r"[\\/]env[\\/]",
    r"[\\/]\.env[\\/]",
    r"[\\/]Lib[\\/]site-packages[\\/]",  # Exclude Python site-packages anywhere
    r"node_modules/",
    r"\.egg-info",
    r"build/",
    r"dist/",
    r"\.tox/",
    r"\.mypy_cache",
    r"\.coverage",
    r"htmlcov/",
    r"scripts/check-no-mock\.py$",  # Exclude this script itself
    r"docs/",
    r"docker-compose\.test\.yml$",  # Exclude test compose file
    r"conftest\.py$",  # Exclude pytest configuration
]

COMPILED_EXCLUDE = [re.compile(pattern) for pattern in EXCLUDE_PATTERNS]

# File extensions to check
CHECK_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".json"
}


def should_exclude(path: str) -> bool:
    """Check if a path should be excluded from scanning."""
    for pattern in COMPILED_EXCLUDE:
        if pattern.search(path):
            return True
    return False


def check_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Check a single file for mock patterns.
    
    Returns a list of tuples: (line_number, line_content, matched_pattern)
    """
    findings = []
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, start=1):
                # Skip comments and docstrings that define patterns
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("r\""):
                    continue
                if "Pattern matched:" in line or "r\"test-" in line or "r'test-" in line:
                    continue
                    
                for pattern in COMPILED_PATTERNS:
                    if pattern.search(line):
                        findings.append((line_num, line.strip(), pattern.pattern))
                        break  # Only report first match per line
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
    
    return findings


def scan_directory(root_dir: str) -> List[Tuple[str, int, str, str]]:
    """
    Scan directory for mock patterns.
    
    Returns a list of tuples: (file_path, line_number, line_content, pattern)
    """
    findings = []
    root_path = Path(root_dir).resolve()
    
    for path in root_path.rglob("*"):
        if path.is_file():
            # Check if path should be excluded
            relative_path = str(path.relative_to(root_path))
            if should_exclude(relative_path):
                continue
            
            # Check file extension
            if path.suffix not in CHECK_EXTENSIONS:
                continue
            
            # Check the file
            file_findings = check_file(path)
            for line_num, line_content, pattern in file_findings:
                findings.append((relative_path, line_num, line_content, pattern))
    
    return findings


def main() -> int:
    """Main entry point."""
    # Get repository root
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent
    
    print(f"[SCAN] Scanning {repo_root} for mock data in production code...")
    print(f"       Excluding: tests/, *_test.py, test_*.py, docs/, venv/, etc.")
    print()
    
    findings = scan_directory(str(repo_root))
    
    if findings:
        print("[ERROR] Mock data detected in production code!")
        print()
        print("Found the following issues:")
        print("-" * 80)
        
        for file_path, line_num, line_content, pattern in findings:
            print(f"\nFile: {file_path}:{line_num}")
            print(f"Pattern matched: {pattern[:60]}...")
            print(f"Line content: {line_content[:80]}...")
        
        print()
        print("-" * 80)
        print(f"\nTotal issues found: {len(findings)}")
        print()
        print("[BLOCKED] COMMIT BLOCKED: Please remove all mock data from production code.")
        print("          Mock data should only exist in:")
        print("          - test files (test_*.py, *_test.py)")
        print("          - tests/ directories")
        print("          - docs/ directory")
        print()
        print("[INFO] To bypass this check (NOT RECOMMENDED), use:")
        print("       git commit --no-verify")
        print()
        return 1
    else:
        print("[PASS] No mock data detected in production code.")
        print()
        print("       All clear! Mock data is properly contained in test files only.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
