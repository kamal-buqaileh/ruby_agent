"""Configuration management for Ruby agent."""

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for the Ruby agent."""

    user_name: str
    user_email: str
    root_path: str
    language: str = "ruby"
    agent_id: str = field(default_factory=str)

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """Create config from dictionary."""
        return cls(**data)


class ConfigManager:
    """Manages agent configuration."""

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the config manager.

        Args:
            config_file: Path to config file. Defaults to ~/.ruby_agent/config.json
        """
        if config_file is None:
            config_dir = Path.home() / ".ruby_agent"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "config.json"

        self.config_file = Path(config_file)
        self._config: Optional[AgentConfig] = None

    def generate_agent_id(self, user_email: str) -> str:
        """
        Generate a unique agent ID based on user email and random component.

        The ID format is: {email_hash}-{random_component}
        - email_hash: First 8 characters of SHA256 hash of email (deterministic)
        - random_component: 8 random hex characters (ensures uniqueness)

        Args:
            user_email: User's email address.

        Returns:
            Unique agent ID.
        """
        # Create a hash from the email (normalize to lowercase for consistency)
        normalized_email = user_email.lower().strip()
        email_hash = hashlib.sha256(normalized_email.encode()).hexdigest()[:8]

        # Generate a random component (8 hex chars = 4 bytes)
        random_component = secrets.token_hex(4)

        # Combine to create unique ID
        agent_id = f"{email_hash}-{random_component}"

        # Ensure uniqueness by checking existing configs
        # This is a safety check - collisions are extremely unlikely
        if self.config_file.exists():
            existing_config = self.load()
            if existing_config and existing_config.agent_id == agent_id:
                # If somehow we get a collision, add more randomness
                random_component = secrets.token_hex(8)
                agent_id = f"{email_hash}-{random_component}"

        return agent_id

    def setup(
        self,
        user_name: str,
        user_email: str,
        root_path: str,
        language: str = "ruby",
        agent_id: Optional[str] = None,
    ) -> AgentConfig:
        """
        Set up the agent configuration.

        Args:
            user_name: User's name.
            user_email: User's email address.
            root_path: Root path for the project.
            language: Programming language (default: ruby).
            agent_id: Optional agent ID. If not provided, will be auto-generated.

        Returns:
            Created AgentConfig instance.
        """
        if agent_id is None:
            agent_id = self.generate_agent_id(user_email)

        config = AgentConfig(
            user_name=user_name,
            user_email=user_email,
            root_path=root_path,
            language=language,
            agent_id=agent_id,
        )

        self.save(config)
        return config

    def save(self, config: AgentConfig) -> None:
        """
        Save configuration to file.

        Args:
            config: AgentConfig instance to save.
        """
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)
        self._config = config

    def load(self) -> Optional[AgentConfig]:
        """
        Load configuration from file.

        Returns:
            AgentConfig instance if file exists, None otherwise.
        """
        if self._config is not None:
            return self._config

        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = AgentConfig.from_dict(data)
            return self._config
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def exists(self) -> bool:
        """Check if configuration file exists."""
        return self.config_file.exists()

    def get_config(self) -> Optional[AgentConfig]:
        """Get the current configuration (loads if not already loaded)."""
        return self.load()

