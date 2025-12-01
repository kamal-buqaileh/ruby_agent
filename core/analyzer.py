"""Main analyzer class for Ruby code analysis."""

from pathlib import Path
from typing import Dict, List, Optional

from tree_sitter import Node

from ruby_agent.core.parser import RubyParser
from ruby_agent.core.utils import iter_descendants, text_for
from ruby_agent.extractors import (
    IncludeExtractor,
    MethodExtractor,
    NamespaceExtractor,
)
from ruby_agent.models import ClassSummary


class RubyAnalyzer:
    """Main analyzer for Ruby code using Tree-sitter."""

    def __init__(self, parser: Optional[RubyParser] = None):
        """
        Initialize the Ruby analyzer.

        Args:
            parser: Optional RubyParser instance. Creates a new one if not provided.
        """
        self.parser = parser or RubyParser()
        self._class_registry: Dict[str, str] = {}
        self._classes_by_file: Dict[str, List[str]] = {}

    def build_class_registry(self, root_dir: Path) -> Dict[str, str]:
        """
        Build a registry mapping class names to their file paths.

        Args:
            root_dir: Root directory to scan for Ruby files.

        Returns:
            Dictionary mapping class names to file paths.
        """
        parser = self.parser.get_parser()
        ruby_files = sorted(path for path in root_dir.rglob("*.rb") if path.is_file())
        class_registry: Dict[str, str] = {}
        namespace_extractor = NamespaceExtractor()

        for file_path in ruby_files:
            source_text = file_path.read_text(encoding="utf-8")
            tree = parser.parse(source_text.encode("utf-8"))

            for cls in iter_descendants(tree.root_node):
                if cls.type != "class":
                    continue

                name = text_for(cls.child_by_field_name("name"), source_text.encode("utf-8"))
                if not name:
                    continue

                namespaces = namespace_extractor.extract(cls, source_text.encode("utf-8"))
                full_label = "::".join([*namespaces, name]) if namespaces else name
                class_registry[full_label] = str(file_path)

                # Also register just the class name without namespace
                if name not in class_registry:
                    class_registry[name] = str(file_path)

                # Track all class name variations for this file
                file_path_str = str(file_path)
                if file_path_str not in self._classes_by_file:
                    self._classes_by_file[file_path_str] = []

                # Generate all possible class name variations
                variations = self._generate_class_name_variations(name, namespaces)
                for variation in variations:
                    if variation not in self._classes_by_file[file_path_str]:
                        self._classes_by_file[file_path_str].append(variation)

        self._class_registry = class_registry
        return class_registry

    def analyze_file(self, file_path: Path) -> List[dict]:
        """
        Analyze a single Ruby file and extract class information.

        Args:
            file_path: Path to the Ruby file to analyze.

        Returns:
            List of class node dictionaries.
        """
        parser = self.parser.get_parser()
        source_text = file_path.read_text(encoding="utf-8")
        source_bytes = source_text.encode("utf-8")
        tree = parser.parse(source_bytes)

        return self._summarize(tree.root_node, source_bytes, file_path)

    def analyze_directory(self, root_dir: Path) -> List[dict]:
        """
        Analyze all Ruby files in a directory.

        Args:
            root_dir: Root directory to scan for Ruby files.

        Returns:
            List of all class node dictionaries.
        """
        # Build class registry first
        self.build_class_registry(root_dir)

        # Analyze all files
        parser = self.parser.get_parser()
        ruby_files = sorted(path for path in root_dir.rglob("*.rb") if path.is_file())
        all_nodes: List[dict] = []

        for file_path in ruby_files:
            file_nodes = self.analyze_file(file_path)
            all_nodes.extend(file_nodes)

        return all_nodes

    def _summarize(self, tree_root: Node, source: bytes, file_path: Path) -> List[dict]:
        """
        Summarize classes in a parsed tree.

        Args:
            tree_root: Root node of the parsed tree.
            source: Source code bytes.
            file_path: Path to the source file.

        Returns:
            List of class node dictionaries.
        """
        namespace_extractor = NamespaceExtractor()
        include_extractor = IncludeExtractor()
        method_extractor = MethodExtractor(self._class_registry)

        summaries: List[ClassSummary] = []

        for cls in iter_descendants(tree_root):
            if cls.type != "class":
                continue

            name = text_for(cls.child_by_field_name("name"), source) or "<anonymous>"
            superclass = text_for(cls.child_by_field_name("superclass"), source)
            includes = include_extractor.extract(cls, source)
            methods = method_extractor.extract(cls, source)
            namespaces = namespace_extractor.extract(cls, source)

            summaries.append(
                ClassSummary(
                    class_name=name,
                    superclass=superclass,
                    namespaces=namespaces,
                    includes=includes,
                    methods=methods,
                )
            )

        return [summary.to_dict(str(file_path)) for summary in summaries]

    def format_nodes(self, nodes: List[dict]) -> List[dict]:
        """
        Format nodes with IDs, positions, and default color.

        Args:
            nodes: List of node dictionaries.

        Returns:
            Formatted nodes with IDs and positions.
        """
        formatted = []
        for index, node in enumerate(nodes, start=1):
            formatted_node = node.copy()
            formatted_node["id"] = str(index)
            formatted_node["position"] = {"x": 0, "y": index * 150}
            formatted_node.setdefault("color", "#6ede87")
            formatted.append(formatted_node)
        return formatted

    def _generate_class_name_variations(self, class_name: str, namespaces: List[str]) -> List[str]:
        """
        Generate all possible class name variations for a given class.

        For a class like Api::V1::UsersController, this generates:
        - Api::V1::UsersController (full path)
        - V1::UsersController (without outer namespace)
        - UsersController (just class name)
        - ::UsersController (absolute root reference)

        Args:
            class_name: The class name.
            namespaces: List of namespace names.

        Returns:
            List of all possible class name variations.
        """
        variations: List[str] = []

        # Full path and partial paths: Api::V1::UsersController, V1::UsersController, etc.
        # Generate all suffixes of the namespace chain
        for i in range(len(namespaces) + 1):
            if i == len(namespaces):
                # Just the class name (no namespaces)
                variations.append(class_name)
            else:
                partial_path = "::".join([*namespaces[i:], class_name])
                variations.append(partial_path)

        # Absolute root reference: ::UsersController
        variations.append(f"::{class_name}")

        return variations

    def build_classes_dictionary(self) -> Dict[str, List[str]]:
        """
        Build a dictionary mapping file paths to arrays of all possible class name variations.

        Returns:
            Dictionary mapping file paths to lists of class name variations.
        """
        return self._classes_by_file.copy()

