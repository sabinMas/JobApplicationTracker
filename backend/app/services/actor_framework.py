"""Actor framework for pluggable, reusable scrapers."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ActorInput(BaseModel):
    """Base class for actor inputs. Subclass for each actor."""
    pass


class ActorOutput(BaseModel):
    """Base class for actor outputs. Subclass for each actor."""
    pass


class Actor(ABC):
    """Base class for all scrapers. Implement in subclasses."""

    name: str = None  # "linkedin", "indeed", etc.
    version: str = "1.0.0"

    def __init__(self):
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must set 'name'")

    @abstractmethod
    async def run(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute the actor with the given config.

        Args:
            config: Actor-specific input configuration

        Returns:
            List of items (dicts) scraped/extracted
        """
        pass

    async def validate_input(self, config: Dict[str, Any]) -> bool:
        """Override to validate config before running."""
        return True

    async def on_success(self, run_id: int, items: List[Dict[str, Any]]) -> None:
        """Hook called after successful run. Override to handle results."""
        pass

    async def on_error(self, run_id: int, error: Exception) -> None:
        """Hook called after error. Override to handle cleanup."""
        pass


class ActorRegistry:
    """Registry of available actors."""

    _registry: Dict[str, Actor] = {}

    @classmethod
    def register(cls, actor: Actor) -> None:
        """Register an actor."""
        name = actor.name
        if name in cls._registry:
            logger.warning(f"Actor '{name}' already registered, overwriting")
        cls._registry[name] = actor
        logger.info(f"Registered actor: {name}")

    @classmethod
    def get(cls, name: str) -> Optional[Actor]:
        """Get an actor by name."""
        return cls._registry.get(name)

    @classmethod
    def list(cls) -> List[str]:
        """List all registered actor names."""
        return list(cls._registry.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if an actor is registered."""
        return name in cls._registry


# Singleton instance for easy access
actor_registry = ActorRegistry()
