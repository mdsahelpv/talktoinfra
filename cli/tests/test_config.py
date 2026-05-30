"""Tests for CLI configuration."""

import json
import tempfile
from pathlib import Path

from talktoinfra_cli.config import CLIConfig


def test_config_defaults():
    config = CLIConfig()
    assert config.orchestrator_url == "http://localhost:8000"
    assert config.api_key == ""
