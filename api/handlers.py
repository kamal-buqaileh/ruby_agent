"""API handlers for the Ruby agent server."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ruby_agent.core.analyzer import RubyAnalyzer


class APIHandlers:
    """Collection of API handlers for the Ruby agent."""

    def __init__(self, analyzer: Optional[RubyAnalyzer] = None):
        """
        Initialize API handlers.

        Args:
            analyzer: Optional RubyAnalyzer instance. Creates a new one if not provided.
        """
        self.analyzer = analyzer or RubyAnalyzer()

    def analyze_directory_handler(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle analyze directory request.

        Expected request data:
            {
                "root": "/path/to/ruby/project",
                "output": "output/nodes.json"  # optional
            }

        Returns:
            {
                "success": true,
                "nodes_count": 10,
                "files_count": 5,
                "output_path": "output/nodes.json",
                "classes_dict_path": "output/classes_dictionary.json"
            }
        """
        try:
            root_path = Path(request_data.get("root", ""))
            if not root_path.exists():
                return {"success": False, "error": f"Path not found: {root_path}"}

            if not root_path.is_dir():
                return {"success": False, "error": f"Path must be a directory: {root_path}"}

            output_path = Path(request_data.get("output", "nodes.json"))
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)

            nodes = self.analyzer.analyze_directory(root_path)
            formatted_nodes = self.analyzer.format_nodes(nodes)
            classes_dict = self.analyzer.build_classes_dictionary()

            # Write nodes.json
            nodes_output = output_dir / output_path.name
            nodes_output.write_text(
                json.dumps(formatted_nodes, indent=2), encoding="utf-8"
            )

            # Write classes_dictionary.json
            classes_output = output_dir / "classes_dictionary.json"
            classes_output.write_text(
                json.dumps(classes_dict, indent=2, sort_keys=True), encoding="utf-8"
            )

            return {
                "success": True,
                "nodes_count": len(formatted_nodes),
                "files_count": len(classes_dict),
                "output_path": str(nodes_output),
                "classes_dict_path": str(classes_output),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_handler(self, request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle health check request.

        Returns:
            {"status": "healthy"}
        """
        return {"status": "healthy"}

