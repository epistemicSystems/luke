"""
Insight Graph storage and operations.

Git-like versioned graph with commit/diff/revert capabilities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from .models import (
    Build,
    Decision,
    Insight,
    Issue,
    Message,
    Persona,
    Thread,
    User,
)


class InsightGraph:
    """
    Core graph storage with Git-like versioning.

    Stores all entities as JSON files with version history.
    Provides query, update, and timeline operations.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Entity type directories
        self.users_dir = self.data_dir / "users"
        self.messages_dir = self.data_dir / "messages"
        self.threads_dir = self.data_dir / "threads"
        self.issues_dir = self.data_dir / "issues"
        self.builds_dir = self.data_dir / "builds"
        self.personas_dir = self.data_dir / "personas"
        self.insights_dir = self.data_dir / "insights"
        self.decisions_dir = self.data_dir / "decisions"

        for dir_path in [
            self.users_dir,
            self.messages_dir,
            self.threads_dir,
            self.issues_dir,
            self.builds_dir,
            self.personas_dir,
            self.insights_dir,
            self.decisions_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Version log
        self.version_log_path = self.data_dir / "version_log.jsonl"

    # === Core CRUD ===

    def save_user(self, user: User) -> None:
        """Save or update a user."""
        self._save_entity(self.users_dir, user.id, user)

    def get_user(self, user_id: UUID) -> Optional[User]:
        """Retrieve a user by ID."""
        return self._load_entity(self.users_dir, user_id, User)

    def get_user_by_discord_id(self, discord_id: str) -> Optional[User]:
        """Retrieve a user by Discord ID."""
        for user_path in self.users_dir.glob("*.json"):
            user = User.model_validate_json(user_path.read_text())
            if user.discord_id == discord_id:
                return user
        return None

    def save_message(self, message: Message) -> None:
        """Save or update a message."""
        self._save_entity(self.messages_dir, message.id, message)

    def get_message(self, message_id: UUID) -> Optional[Message]:
        """Retrieve a message by ID."""
        return self._load_entity(self.messages_dir, message_id, Message)

    def save_thread(self, thread: Thread) -> None:
        """Save or update a thread."""
        self._save_entity(self.threads_dir, thread.id, thread)

    def get_thread(self, thread_id: UUID) -> Optional[Thread]:
        """Retrieve a thread by ID."""
        return self._load_entity(self.threads_dir, thread_id, Thread)

    def save_issue(self, issue: Issue) -> None:
        """Save or update an issue."""
        self._save_entity(self.issues_dir, issue.id, issue)

    def get_issue(self, issue_id: UUID) -> Optional[Issue]:
        """Retrieve an issue by ID."""
        return self._load_entity(self.issues_dir, issue_id, Issue)

    def save_build(self, build: Build) -> None:
        """Save a build record."""
        self._save_entity(self.builds_dir, build.id, build)

    def get_build(self, build_id: UUID) -> Optional[Build]:
        """Retrieve a build by ID."""
        return self._load_entity(self.builds_dir, build_id, Build)

    def save_persona(self, persona: Persona) -> None:
        """Save or update a persona."""
        self._save_entity(self.personas_dir, persona.id, persona)

    def get_persona(self, persona_id: UUID) -> Optional[Persona]:
        """Retrieve a persona by ID."""
        return self._load_entity(self.personas_dir, persona_id, Persona)

    def save_insight(self, insight: Insight) -> None:
        """Save an insight."""
        self._save_entity(self.insights_dir, insight.id, insight)

    def get_insight(self, insight_id: UUID) -> Optional[Insight]:
        """Retrieve an insight by ID."""
        return self._load_entity(self.insights_dir, insight_id, Insight)

    def save_decision(self, decision: Decision) -> None:
        """Save a decision."""
        self._save_entity(self.decisions_dir, decision.id, decision)

    def get_decision(self, decision_id: UUID) -> Optional[Decision]:
        """Retrieve a decision by ID."""
        return self._load_entity(self.decisions_dir, decision_id, Decision)

    # === Query operations ===

    def list_users(self, limit: Optional[int] = None) -> list[User]:
        """List all users."""
        return self._list_entities(self.users_dir, User, limit)

    def list_messages(
        self, channel_id: Optional[str] = None, limit: Optional[int] = None
    ) -> list[Message]:
        """List messages, optionally filtered by channel."""
        messages = self._list_entities(self.messages_dir, Message, limit)
        if channel_id:
            messages = [m for m in messages if m.channel_id == channel_id]
        return messages

    def list_threads(self, channel_id: Optional[str] = None) -> list[Thread]:
        """List threads, optionally filtered by channel."""
        threads = self._list_entities(self.threads_dir, Thread)
        if channel_id:
            threads = [t for t in threads if t.channel_id == channel_id]
        return threads

    def list_issues(self, status: Optional[str] = None) -> list[Issue]:
        """List issues, optionally filtered by status."""
        issues = self._list_entities(self.issues_dir, Issue)
        if status:
            issues = [i for i in issues if i.status.value == status]
        return issues

    def list_personas(self) -> list[Persona]:
        """List all personas."""
        return self._list_entities(self.personas_dir, Persona)

    def list_insights(self) -> list[Insight]:
        """List all insights."""
        return self._list_entities(self.insights_dir, Insight)

    # === Timeline / Version operations ===

    def log_change(
        self, entity_type: str, entity_id: UUID, action: str, details: dict[str, Any]
    ) -> None:
        """
        Log a change to the version history.

        Args:
            entity_type: Type of entity (user, message, issue, etc.)
            entity_id: ID of the entity
            action: Action performed (create, update, delete, tag, etc.)
            details: Additional context
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action,
            "details": details,
        }

        with open(self.version_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_timeline(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve version history.

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            since: Filter by timestamp

        Returns:
            List of log entries matching filters
        """
        if not self.version_log_path.exists():
            return []

        entries = []
        with open(self.version_log_path) as f:
            for line in f:
                entry = json.loads(line)

                # Apply filters
                if entity_type and entry["entity_type"] != entity_type:
                    continue
                if entity_id and entry["entity_id"] != str(entity_id):
                    continue
                if since:
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if entry_time < since:
                        continue

                entries.append(entry)

        return entries

    # === Internal helpers ===

    def _save_entity(self, directory: Path, entity_id: UUID, entity: Any) -> None:
        """Generic entity save."""
        path = directory / f"{entity_id}.json"
        path.write_text(entity.model_dump_json(indent=2))

        # Log the change
        self.log_change(
            entity_type=directory.name,
            entity_id=entity_id,
            action="create" if not path.exists() else "update",
            details={"path": str(path)},
        )

    def _load_entity(self, directory: Path, entity_id: UUID, model_class: type) -> Optional[Any]:
        """Generic entity load."""
        path = directory / f"{entity_id}.json"
        if not path.exists():
            return None
        return model_class.model_validate_json(path.read_text())

    def _list_entities(
        self, directory: Path, model_class: type, limit: Optional[int] = None
    ) -> list[Any]:
        """Generic entity list."""
        entities = []
        for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            entities.append(model_class.model_validate_json(path.read_text()))
            if limit and len(entities) >= limit:
                break
        return entities
