"""Data models for Ruby code analysis."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClassSummary:
    """Summary of a Ruby class."""

    class_name: str
    superclass: Optional[str]
    namespaces: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    methods: List[dict] = field(default_factory=list)

    def to_dict(self, file_path: str) -> dict:
        """
        Convert the class summary to a dictionary representation.

        Args:
            file_path: The file path where this class is defined.

        Returns:
            Dictionary representation of the class.
        """
        full_label = (
            "::".join([*self.namespaces, self.class_name])
            if self.namespaces
            else self.class_name
        )
        ordered_namespaces = [
            {"name": name, "order": position}
            for position, name in enumerate(self.namespaces, start=1)
        ]
        return {
            "label": full_label,
            "class_type": "class",
            "file_path": file_path,
            "inheritance": self.superclass,
            "includes": self.includes,
            "namespaces": ordered_namespaces,
            "namespace_chain": [*self.namespaces, self.class_name],
            "methods": self.methods,
        }

