"""
Custom Database Session Service with EventCompaction Fix

This module provides a fixed version of ADK's DatabaseSessionService that properly
deserializes EventCompaction objects from the database.

The issue: ADK's default implementation uses model_copy(update=model_dump()) which
converts nested Pydantic models like EventCompaction to dicts, causing AttributeError
when the code tries to access .start_timestamp on a dict.

The fix: Monkey-patch StorageEvent.to_event() to reconstruct EventCompaction objects
from dicts during deserialization.

Technical term: Runtime Method Replacement (Monkey Patching)
"""

from google.adk.events.event_actions import EventCompaction
from google.adk.events.event import Event, EventActions
from google.adk.sessions.database_session_service import (
    DatabaseSessionService as _BaseSessionService,
    StorageEvent
)
from typing import Optional
from sqlalchemy.ext.asyncio import async_sessionmaker


class FixedDatabaseSessionService(_BaseSessionService):
    """Custom session service that fixes EventCompaction deserialization.
    
    This class inherits from DatabaseSessionService and applies a runtime patch
    (monkey-patch) to fix the compaction deserialization issue.
    
    Usage:
        session_service = FixedDatabaseSessionService(db_url="sqlite+aiosqlite:///path/to/db")
    """
    
    @staticmethod
    def _fix_compaction(actions_dict: dict) -> dict:
        """Convert compaction dict back to EventCompaction object if needed.
        
        Args:
            actions_dict: Dictionary containing event actions, possibly with compaction data
            
        Returns:
            Modified dictionary with EventCompaction object instead of dict
        """
        if 'compaction' in actions_dict and actions_dict['compaction'] is not None:
            compaction_data = actions_dict['compaction']
            if isinstance(compaction_data, dict):
                # Reconstruct EventCompaction from dict
                actions_dict['compaction'] = EventCompaction(**compaction_data)
        return actions_dict
    
    def __init__(self, *, db_url: str, database_session_factory: Optional[async_sessionmaker] = None):
        """Initialize the fixed session service.
        
        Args:
            db_url: Database connection URL (e.g., "sqlite+aiosqlite:///path/to/db")
            database_session_factory: Optional custom session factory
        """
        # Only pass database_session_factory if it's not None (avoids SQLAlchemy error)
        if database_session_factory is not None:
            super().__init__(db_url=db_url, database_session_factory=database_session_factory)
        else:
            super().__init__(db_url=db_url)
        
        # Monkey-patch StorageEvent.to_event to fix compaction deserialization
        original_to_event = StorageEvent.to_event
        
        def fixed_to_event(self) -> Event:
            """Patched version that reconstructs EventCompaction objects."""
            # Get the actions dict and fix compaction before creating EventActions
            actions_dict = self.actions.model_dump() if self.actions else {}
            actions_dict = FixedDatabaseSessionService._fix_compaction(actions_dict)
            
            return Event(
                id=self.id,
                invocation_id=self.invocation_id,
                author=self.author,
                branch=self.branch,
                actions=EventActions(**actions_dict),  # Use fixed dict instead of model_copy
                timestamp=self.timestamp.timestamp(),
                long_running_tool_ids=self.long_running_tool_ids,
                partial=self.partial,
                turn_complete=self.turn_complete,
                error_code=self.error_code,
                error_message=self.error_message,
                interrupted=self.interrupted,
                custom_metadata=self.custom_metadata,
                content=self.content,
                grounding_metadata=self.grounding_metadata,
                usage_metadata=self.usage_metadata,
                citation_metadata=self.citation_metadata,
                input_transcription=self.input_transcription,
                output_transcription=self.output_transcription,
            )
        
        # Apply the patch globally to StorageEvent
        StorageEvent.to_event = fixed_to_event
