# Configuration file for the Sphinx documentation builder.

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "scitex-notification"
copyright = "2026, Yusuke Watanabe"
author = "Yusuke Watanabe"

try:
    from scitex_notification import __version__

    release = __version__
    version = ".".join(release.split(".")[:2])
except ImportError:
    release = "0.1.0"
    version = "0.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autodoc_mock_imports = [
    "twilio",
    "mcp",
    "fastmcp",
    "playwright",
    "scitex_audio",
]

autosummary_generate = True

html_theme = "sphinx_rtd_theme"
html_static_path = []

html_theme_options = {
    "navigation_depth": 4,
    "titles_only": False,
}

html_context = {
    "display_github": True,
    "github_user": "ywatanabe1989",
    "github_repo": "scitex-notification",
    "github_version": "main",
    "conf_py_path": "/docs/sphinx/",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
