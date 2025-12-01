"""Extractors for Ruby code analysis."""

from typing import Dict, List, Optional, Set

from tree_sitter import Node

from ruby_agent.core.utils import is_within_method, iter_descendants, text_for


class NamespaceExtractor:
    """Extracts namespace information from class nodes."""

    @staticmethod
    def extract(class_node: Node, source: bytes) -> List[str]:
        """
        Extract namespace chain from a class node.

        Args:
            class_node: The class node to extract namespaces from.
            source: The source code bytes.

        Returns:
            List of namespace names in order from outer to inner.
        """
        namespaces: List[str] = []
        parent = class_node.parent

        while parent is not None:
            if parent.type in {"module", "class"}:
                name = text_for(parent.child_by_field_name("name"), source)
                if name:
                    namespaces.append(name)
            parent = parent.parent

        namespaces.reverse()
        return namespaces


class IncludeExtractor:
    """Extracts included modules from class nodes."""

    @staticmethod
    def extract(class_node: Node, source: bytes) -> List[str]:
        """
        Extract all included modules from a class.

        Args:
            class_node: The class node to extract includes from.
            source: The source code bytes.

        Returns:
            Sorted list of included module names.
        """
        includes: Set[str] = set()

        for node in iter_descendants(class_node):
            if node.type not in {"call", "command"}:
                continue

            if is_within_method(node):
                continue

            method_node = node.child_by_field_name("method")
            if text_for(method_node, source) != "include":
                continue

            args_node = node.child_by_field_name("argument_list") or node.child_by_field_name("arguments")
            if not args_node:
                continue

            for arg in args_node.named_children:
                value = text_for(arg, source)
                if value:
                    includes.add(value)

        return sorted(includes)


class MethodCallExtractor:
    """Extracts method calls and resolves them to file paths."""

    def __init__(self, class_registry: Optional[Dict[str, str]] = None):
        """
        Initialize the method call extractor.

        Args:
            class_registry: Dictionary mapping class names to file paths.
        """
        self.class_registry = class_registry or {}

    @staticmethod
    def _extract_receiver(call_node: Node) -> Optional[Node]:
        """Extract the receiver node from a call node."""
        receiver = call_node.child_by_field_name("receiver")
        if receiver is None and call_node.type in {"command", "command_call"}:
            receiver = call_node.child_by_field_name("method")

        while receiver is not None and receiver.type == "call":
            receiver = receiver.child_by_field_name("receiver")

        if receiver is None:
            return None

        if receiver.type in {"constant", "scope_resolution"}:
            return receiver

        return None

    def _resolve_file_path(self, name: str) -> Optional[str]:
        """
        Resolve a class name to its file path using the class registry.

        Args:
            name: The class name to resolve.

        Returns:
            File path if found, None otherwise.
        """
        if not self.class_registry:
            return None

        # Try exact match first
        if name in self.class_registry:
            return self.class_registry[name]

        # If name starts with ::, it means root namespace (absolute)
        # Only match root-level classes, NOT namespaced ones (Ruby semantics)
        if name.startswith("::"):
            normalized = name[2:]  # Remove leading ::
            # Only match if it's a root-level class (no :: in the normalized name)
            # This ensures ::Auth matches Auth (root) but NOT Api::Auth
            if normalized in self.class_registry and "::" not in normalized:
                return self.class_registry[normalized]

        # Relative name - try exact match, then suffix match
        # First try exact match (could be root-level or we already know the full name)
        if name in self.class_registry:
            return self.class_registry[name]

        # Try to find any class ending with this name (e.g., "Auth" matches "Api::Auth")
        # This handles relative references that resolve to namespaced classes
        for reg_name, file_path in self.class_registry.items():
            if reg_name.endswith(f"::{name}") or reg_name == name:
                return file_path

        return None

    def extract(self, method_node: Node, source: bytes) -> List[dict]:
        """
        Extract method calls from a method node.

        Args:
            method_node: The method node to extract calls from.
            source: The source code bytes.

        Returns:
            Sorted list of call information dictionaries.
        """
        calls: List[dict] = []
        seen_names: Set[str] = set()

        for node in iter_descendants(method_node):
            if node.type not in {"call", "command", "command_call"}:
                continue

            receiver = self._extract_receiver(node)
            if receiver is None:
                continue

            name = text_for(receiver, source)
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            call_info = {"name": name}
            file_path = self._resolve_file_path(name)
            if file_path:
                call_info["file_path"] = file_path

            calls.append(call_info)

        return sorted(calls, key=lambda x: x["name"])


class MethodExtractor:
    """Extracts method definitions from class nodes."""

    def __init__(self, class_registry: Optional[Dict[str, str]] = None):
        """
        Initialize the method extractor.

        Args:
            class_registry: Dictionary mapping class names to file paths for call resolution.
        """
        self.call_extractor = MethodCallExtractor(class_registry)

    def extract(self, class_node: Node, source: bytes) -> List[dict]:
        """
        Extract all methods from a class node.

        Args:
            class_node: The class node to extract methods from.
            source: The source code bytes.

        Returns:
            List of method information dictionaries.
        """
        methods: List[dict] = []
        for node in iter_descendants(class_node):
            if node.type not in {"method", "singleton_method"}:
                continue

            name = text_for(node.child_by_field_name("name"), source) or "<anonymous>"
            calls = self.call_extractor.extract(node, source)

            method_type = "instance"
            if node.type == "singleton_method":
                method_type = "class"

            methods.append(
                {
                    "name": name,
                    "calls": calls,
                    "method_type": method_type,
                    "visibility": "public",
                }
            )
        return methods

