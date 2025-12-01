"""Ruby parser setup using Tree-sitter."""

import sys
from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Look for tree-sitter-ruby in common locations (Docker container or local)
GRAMMAR_REPO = Path("/tree-sitter-ruby")
BUILD_DIR = Path(__file__).resolve().parent.parent / "build"
LIB_NAME = "ruby.dylib" if sys.platform == "darwin" else "ruby.so"
LANG_LIB = BUILD_DIR / LIB_NAME


class RubyParser:
    """Handles Tree-sitter Ruby parser initialization and setup."""

    def __init__(self, grammar_repo: Optional[Path] = None, build_dir: Optional[Path] = None):
        """
        Initialize the Ruby parser.

        Args:
            grammar_repo: Path to tree-sitter-ruby grammar repository. Defaults to vendor/tree-sitter-ruby.
            build_dir: Directory to build the language library. Defaults to build/.
        """
        self.grammar_repo = grammar_repo or GRAMMAR_REPO
        self.build_dir = build_dir or BUILD_DIR
        self._language: Optional[Language] = None
        self._parser: Optional[Parser] = None

    def ensure_language(self) -> Language:
        """Ensure the Ruby language library is built and return it."""
        if self._language is not None:
            return self._language

        if not self.grammar_repo.exists():
            raise SystemExit(
                f"Ruby grammar not found at {self.grammar_repo}. "
                "Clone https://github.com/tree-sitter/tree-sitter-ruby into vendor/tree-sitter-ruby."
            )

        self.build_dir.mkdir(parents=True, exist_ok=True)
        lang_lib = self.build_dir / LIB_NAME

        if not lang_lib.exists():
            Language.build_library(str(lang_lib), [str(self.grammar_repo)])

        self._language = Language(str(lang_lib), "ruby")
        return self._language

    def get_parser(self) -> Parser:
        """Get or create a configured parser instance."""
        if self._parser is not None:
            return self._parser

        language = self.ensure_language()
        parser = Parser()
        parser.set_language(language)
        self._parser = parser
        return parser

