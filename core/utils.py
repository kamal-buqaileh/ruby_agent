"""Utility functions for tree traversal and text extraction."""

from collections import deque
from typing import Iterable, Optional

from tree_sitter import Node


def iter_descendants(node: Node) -> Iterable[Node]:
    """Iterate over all named descendant nodes in breadth-first order."""
    queue: deque[Node] = deque([node])
    while queue:
        current = queue.popleft()
        yield current
        queue.extend(child for child in current.children if child.is_named)


def text_for(node: Optional[Node], source: bytes) -> Optional[str]:
    """Extract text content from a node."""
    if node is None:
        return None
    return source[node.start_byte : node.end_byte].decode("utf-8")


def is_within_method(node: Node) -> bool:
    """Check if a node is within a method definition."""
    parent = node.parent
    while parent is not None:
        if parent.type in {"method", "singleton_method"}:
            return True
        parent = parent.parent
    return False

