"""
Developer actions for the RAG interface.

Inline actions like:
- Create issue from messages
- Tag messages with labels
- Link messages to issues
- Request repro from user
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from ..core.graph import InsightGraph
from ..core.models import Issue, IssueSeverity, IssueStatus, Message, MessageLabel


class DevActions:
    """Developer actions for manipulating the graph."""

    def __init__(self, graph: InsightGraph):
        self.graph = graph

    def create_issue_from_messages(
        self,
        title: str,
        description: str,
        message_ids: list[UUID],
        severity: IssueSeverity,
        tags: Optional[set[str]] = None,
    ) -> Issue:
        """
        Create a new issue from a set of messages.

        Args:
            title: Issue title
            description: Issue description
            message_ids: Messages to link
            severity: Issue severity
            tags: Optional tags

        Returns:
            Created issue
        """
        issue = Issue(
            title=title,
            description=description,
            linked_message_ids=message_ids,
            severity=severity,
            tags=tags or set(),
        )

        # Extract repro steps from messages if labeled
        for msg_id in message_ids:
            msg = self.graph.get_message(msg_id)
            if msg and MessageLabel.REPRO_STEPS in msg.labels:
                issue.steps_to_repro.append(msg.cleaned_text or msg.text)

        self.graph.save_issue(issue)

        # Update messages to link back to issue
        for msg_id in message_ids:
            msg = self.graph.get_message(msg_id)
            if msg:
                msg.linked_issue_ids.append(issue.id)
                self.graph.save_message(msg)

        return issue

    def tag_message(self, message_id: UUID, label: MessageLabel) -> None:
        """
        Add a label to a message.

        Args:
            message_id: Message to tag
            label: Label to add
        """
        msg = self.graph.get_message(message_id)
        if not msg:
            raise ValueError(f"Message {message_id} not found")

        msg.labels.add(label)
        self.graph.save_message(msg)

        self.graph.log_change(
            entity_type="message",
            entity_id=message_id,
            action="tag",
            details={"label": label.value},
        )

    def link_message_to_issue(self, message_id: UUID, issue_id: UUID) -> None:
        """
        Link a message to an issue.

        Args:
            message_id: Message ID
            issue_id: Issue ID
        """
        msg = self.graph.get_message(message_id)
        issue = self.graph.get_issue(issue_id)

        if not msg or not issue:
            raise ValueError("Message or issue not found")

        # Link both ways
        if issue_id not in msg.linked_issue_ids:
            msg.linked_issue_ids.append(issue_id)
            self.graph.save_message(msg)

        if message_id not in issue.linked_message_ids:
            issue.linked_message_ids.append(message_id)
            self.graph.save_issue(issue)

        self.graph.log_change(
            entity_type="message",
            entity_id=message_id,
            action="link_to_issue",
            details={"issue_id": str(issue_id)},
        )

    def update_issue_status(self, issue_id: UUID, status: IssueStatus, owner: Optional[str] = None) -> None:
        """
        Update issue status and optionally assign owner.

        Args:
            issue_id: Issue ID
            status: New status
            owner: Optional owner username
        """
        issue = self.graph.get_issue(issue_id)
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")

        old_status = issue.status
        issue.status = status
        issue.updated_at = datetime.utcnow()

        if owner:
            issue.owner_id = owner

        self.graph.save_issue(issue)

        self.graph.log_change(
            entity_type="issue",
            entity_id=issue_id,
            action="status_change",
            details={
                "old_status": old_status.value,
                "new_status": status.value,
                "owner": owner,
            },
        )

    def create_insight(self, hypothesis: str, evidence_message_ids: list[UUID], confidence: float) -> UUID:
        """
        Create a new insight from messages.

        Args:
            hypothesis: The insight hypothesis
            evidence_message_ids: Supporting message IDs
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            Insight ID
        """
        from ..core.models import Insight

        evidence_refs = [{"type": "message", "id": str(msg_id)} for msg_id in evidence_message_ids]

        insight = Insight(
            hypothesis=hypothesis,
            evidence_refs=evidence_refs,
            confidence=confidence,
            author="system",
        )

        self.graph.save_insight(insight)
        return insight.id

    def get_issue_bundle(self, tag: str, limit: int = 10) -> list[Issue]:
        """
        Get a bundle of issues by tag for batch operations.

        Args:
            tag: Tag to filter by
            limit: Max number of issues

        Returns:
            List of issues
        """
        all_issues = self.graph.list_issues()
        filtered = [issue for issue in all_issues if tag in issue.tags]
        return filtered[:limit]
