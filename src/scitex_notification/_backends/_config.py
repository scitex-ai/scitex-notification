#!/usr/bin/env python3
# Timestamp: "2026-01-13 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_backends/_config.py

"""Configuration for notification backends (standalone).

Priority resolution:
    direct → config (YAML) → env → default

Configuration sources:
1. YAML file: path from SCITEX_NOTIFICATION_CONFIG env var
2. ``~/.scitex/notification/config.yaml`` (canonical scitex fallback, SCITEX_DIR-aware)
3. Environment variables: SCITEX_NOTIFICATION_*

Env file sourcing:
    If SCITEX_NOTIFICATION_ENV_SRC is set, that file is sourced before
    reading any other env vars.

Example YAML:
    notification:
      default_backend: audio
      backend_priority:
        - audio
        - desktop
        - email
      level_backends:
        info: [audio]
        warning: [audio, desktop]
        error: [audio, desktop, email]
        critical: [audio, desktop, email]
      timeouts:
        matplotlib: 5.0
        playwright: 5.0

Environment variables:
    SCITEX_NOTIFICATION_CONFIG: Path to custom config YAML file (overrides ``~/.scitex/notification/config.yaml``)
    SCITEX_NOTIFICATION_ENV_SRC: Path to env file to source before reading vars
    SCITEX_NOTIFICATION_DEFAULT_BACKEND: audio
    SCITEX_NOTIFICATION_BACKEND_PRIORITY: audio,desktop,email (comma-separated)
    SCITEX_NOTIFICATION_INFO_BACKENDS: audio
    SCITEX_NOTIFICATION_WARNING_BACKENDS: audio,desktop
    SCITEX_NOTIFICATION_ERROR_BACKENDS: audio,desktop,email
    SCITEX_NOTIFICATION_CRITICAL_BACKENDS: audio,desktop,email
    SCITEX_NOTIFICATION_TIMEOUT_MATPLOTLIB: 5.0
    SCITEX_NOTIFICATION_TIMEOUT_PLAYWRIGHT: 5.0
"""

from __future__ import annotations

import importlib.util
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ._types import NotifyLevel

# Backend package requirements
BACKEND_PACKAGES = {
    "audio": None,  # Uses scitex_audio (optional)
    "desktop": None,  # Uses PowerShell on WSL (no package needed)
    "emacs": None,  # Uses emacsclient (no Python package needed)
    "matplotlib": "matplotlib",
    "playwright": "playwright",
    "email": None,  # Uses stdlib smtplib
    "webhook": None,  # Uses stdlib urllib
}


@lru_cache(maxsize=16)
def is_package_available(package: str) -> bool:
    """Check if a Python package is available."""
    if package is None:
        return True
    return importlib.util.find_spec(package) is not None


def is_backend_available(backend: str) -> bool:
    """Check if a backend's required packages are available."""
    package = BACKEND_PACKAGES.get(backend)
    return is_package_available(package)


# Default configuration (used if not in YAML)
DEFAULT_CONFIG = {
    "default_backend": "audio",
    "backend_priority": [
        "audio",
        "emacs",
        "desktop",
        "matplotlib",
        "playwright",
        "email",
        "webhook",
    ],
    "level_backends": {
        "info": ["audio"],
        "warning": ["audio", "emacs"],
        "error": ["audio", "emacs", "desktop", "email"],
        "critical": ["audio", "emacs", "desktop", "matplotlib", "email"],
    },
    "timeouts": {
        "matplotlib": 5.0,
        "playwright": 5.0,
    },
}


def _source_env_file(path: str) -> None:
    """Read a simple KEY=VALUE env file and set vars into os.environ."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Strip export prefix if present
                if line.startswith("export "):
                    line = line[len("export ") :]
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
    except Exception:
        pass


def _load_yaml_config(config_path: str) -> dict:
    """Load a YAML config file, returning empty dict on failure."""
    try:
        import yaml  # type: ignore[import]

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        # Support both "notification:" and "ui:" top-level keys
        return data.get("notification") or data.get("ui") or {}
    except Exception:
        return {}


def _scitex_notification_dir() -> Path:
    """Return the canonical user-scope root for scitex-notification.

    Honours ``$SCITEX_DIR`` per ecosystem local-state-directories §6.
    Returns ``~/.scitex/notification/`` (or ``$SCITEX_DIR/notification/``)
    with lazy mkdir.
    """
    base = Path(
        os.environ.get(
            "SCITEX_DIR",
            os.path.join(os.path.expanduser("~"), ".scitex"),
        )
    )
    pkg_dir = base / "notification"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    return pkg_dir


def _scitex_notification_runtime_dir() -> Path:
    """Return the runtime directory for scitex-notification.

    Returns ``<scitex-dir>/notification/runtime/`` with lazy mkdir.
    This is where regenerable data (cache, logs, PID files, etc.)
    belongs per ecosystem local-state-directories §4b.
    """
    rt_dir = _scitex_notification_dir() / "runtime"
    rt_dir.mkdir(parents=True, exist_ok=True)
    return rt_dir


def _resolve_default_config_path() -> Optional[str]:
    """Resolve the default config path via the canonical scitex layout.

    Returns
    -------
    str or None
        ``~/.scitex/notification/config.yaml`` (or SCITEX_DIR equivalent)
        if the file exists, otherwise None.
    """
    path = _scitex_notification_dir() / "config.yaml"
    return str(path) if path.exists() else None


class UIConfig:
    """Configuration manager for scitex_notification (standalone)."""

    _instance: Optional[UIConfig] = None
    _config: dict

    def __new__(cls, config_path: Optional[str] = None):
        # Allow creating new instance with custom path
        if config_path is not None:
            instance = super().__new__(cls)
            instance._config = {}
            instance._config_path = config_path
            instance._load_config()
            return instance

        # Otherwise use singleton
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            cls._instance._config_path = None
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from env file, YAML, and environment variables."""
        self._config = DEFAULT_CONFIG.copy()
        self._config["level_backends"] = DEFAULT_CONFIG["level_backends"].copy()
        self._config["timeouts"] = DEFAULT_CONFIG["timeouts"].copy()

        # 1. Source env file if specified
        env_src = os.getenv("SCITEX_NOTIFICATION_ENV_SRC")
        if env_src:
            _source_env_file(env_src)

        # 2. Load YAML config if a path is available
        config_path = (
            self._config_path
            or os.getenv("SCITEX_NOTIFICATION_CONFIG")
            or _resolve_default_config_path()
        )
        if config_path:
            yaml_config = _load_yaml_config(config_path)
            if yaml_config:
                if "default_backend" in yaml_config:
                    self._config["default_backend"] = yaml_config["default_backend"]
                if "backend_priority" in yaml_config:
                    self._config["backend_priority"] = yaml_config["backend_priority"]
                if "level_backends" in yaml_config:
                    for level, backends in yaml_config["level_backends"].items():
                        self._config["level_backends"][level] = backends
                if "timeouts" in yaml_config:
                    self._config["timeouts"].update(yaml_config["timeouts"])

        # 3. Override with environment variables (lowest priority after config)
        self._load_env_overrides()

    def _load_env_overrides(self):
        """Load environment variable overrides from SCITEX_NOTIFICATION_* vars."""
        default_backend = os.getenv("SCITEX_NOTIFICATION_DEFAULT_BACKEND")
        if default_backend:
            self._config["default_backend"] = default_backend

        backend_priority = os.getenv("SCITEX_NOTIFICATION_BACKEND_PRIORITY")
        if backend_priority:
            self._config["backend_priority"] = backend_priority.split(",")

        # Level-specific backends from env
        for level in ["info", "warning", "error", "critical"]:
            level_upper = level.upper()
            env_val = os.getenv(f"SCITEX_NOTIFICATION_{level_upper}_BACKENDS")
            if env_val:
                self._config["level_backends"][level] = env_val.split(",")

        # Timeouts from env
        for backend in ["matplotlib", "playwright"]:
            backend_upper = backend.upper()
            env_val = os.getenv(f"SCITEX_NOTIFICATION_TIMEOUT_{backend_upper}")
            if env_val:
                try:
                    self._config["timeouts"][backend] = float(env_val)
                except ValueError:
                    pass

    @property
    def default_backend(self) -> str:
        return self._config.get("default_backend", "audio")

    @property
    def backend_priority(self) -> list[str]:
        return self._config.get("backend_priority", ["audio"])

    def get_available_backend_priority(self) -> list[str]:
        """Get backend priority filtered by package availability."""
        return [b for b in self.backend_priority if is_backend_available(b)]

    def get_backends_for_level(self, level: NotifyLevel) -> list[str]:
        """Get configured backends for a notification level."""
        level_backends = self._config.get("level_backends", {})
        return level_backends.get(level.value, [self.default_backend])

    def get_available_backends_for_level(self, level: NotifyLevel) -> list[str]:
        """Get backends for level filtered by package availability."""
        backends = self.get_backends_for_level(level)
        return [b for b in backends if is_backend_available(b)]

    def get_first_available_backend(self) -> str:
        """Get first available backend from priority list."""
        for backend in self.backend_priority:
            if is_backend_available(backend):
                return backend
        return self.default_backend

    def get_timeout(self, backend: str) -> float:
        """Get timeout for a backend."""
        timeouts = self._config.get("timeouts", {})
        value = timeouts.get(backend, 5.0)
        return float(value) if value is not None else 5.0

    def reload(self):
        """Reload configuration from files."""
        self._load_config()

    @classmethod
    def reset(cls):
        """Reset singleton instance (useful for testing)."""
        cls._instance = None


def get_config(config_path: Optional[str] = None) -> UIConfig:
    """Get the notification configuration instance.

    Parameters
    ----------
    config_path : str, optional
        Path to custom config file. If provided, creates new instance.
        Otherwise returns cached singleton.
    """
    if config_path:
        return UIConfig(config_path)
    return UIConfig()


# EOF
