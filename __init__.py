"""Ruby Agent - A Tree-sitter based Ruby code analyzer."""

__version__ = "1.0.0"

# Main exports
from ruby_agent.core.analyzer import RubyAnalyzer
from ruby_agent.core.parser import RubyParser

__all__ = [
    "RubyAnalyzer",
    "RubyParser",
]
