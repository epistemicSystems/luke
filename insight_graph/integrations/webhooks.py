"""
Webhook handlers for external integrations.

Receives webhooks from Discord, helpdesk systems, etc.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..core.graph import InsightGraph
from ..core.models import Issue, IssueSeverity, IssueStatus, Message, MessageLabel, User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class DiscordWebhook(BaseModel):
    """Discord webhook payload."""

    user_id: str
    username: str
    channel_id: str
    message_id: str
    content: str
    timestamp: str


class HelpdeskWebhook(BaseModel):
    """Generic helpdesk ticket webhook."""

    ticket_id: str
    title: str
    description: str
    priority: str
    status: str
    reporter_email: Optional[str] = None
    tags: list[str] = []


@router.post("/discord")
async def handle_discord_webhook(webhook: DiscordWebhook, graph: InsightGraph):
    """
    Handle incoming Discord webhook.

    This is an alternative to the Discord bot for environments where
    bot installation isn't possible.
    """
    # Get or create user
    user = graph.get_user_by_discord_id(webhook.user_id)
    if not user:
        user = User(
            discord_id=webhook.user_id,
            discord_handle=webhook.username,
        )
        graph.save_user(user)

    # Create message
    msg = Message(
        user_id=user.id,
        discord_message_id=webhook.message_id,
        channel_id=webhook.channel_id,
        text=webhook.content,
        cleaned_text=webhook.content,
    )

    # Auto-label (simple version)
    if "bug" in webhook.content.lower() or "crash" in webhook.content.lower():
        msg.labels.add(MessageLabel.BUG_REPORT)
    if "fps" in webhook.content.lower() or "lag" in webhook.content.lower():
        msg.labels.add(MessageLabel.PERFORMANCE)

    graph.save_message(msg)

    return {
        "status": "success",
        "message_id": str(msg.id),
    }


@router.post("/helpdesk")
async def handle_helpdesk_webhook(webhook: HelpdeskWebhook, graph: InsightGraph):
    """
    Handle incoming helpdesk ticket webhook.

    Converts helpdesk tickets to issues in the graph.
    """
    # Map priority to severity
    severity_map = {
        "low": IssueSeverity.LOW,
        "medium": IssueSeverity.MEDIUM,
        "high": IssueSeverity.HIGH,
        "critical": IssueSeverity.CRITICAL,
    }

    severity = severity_map.get(webhook.priority.lower(), IssueSeverity.MEDIUM)

    # Map status
    status_map = {
        "open": IssueStatus.NEW,
        "in_progress": IssueStatus.IN_PROGRESS,
        "resolved": IssueStatus.RESOLVED,
        "closed": IssueStatus.RESOLVED,
    }

    status = status_map.get(webhook.status.lower(), IssueStatus.NEW)

    # Create issue
    issue = Issue(
        title=webhook.title,
        description=webhook.description,
        severity=severity,
        status=status,
        tags=set(webhook.tags),
    )

    graph.save_issue(issue)

    return {
        "status": "success",
        "issue_id": str(issue.id),
        "ticket_id": webhook.ticket_id,
    }


@router.post("/github")
async def handle_github_webhook(request: Request, graph: InsightGraph):
    """
    Handle GitHub issue webhook.

    Links GitHub issues to the graph for tracking.
    """
    payload = await request.json()

    action = payload.get("action")
    issue_data = payload.get("issue", {})

    if action not in ["opened", "closed"]:
        return {"status": "ignored", "action": action}

    # Create or update issue
    github_id = issue_data.get("number")
    title = issue_data.get("title")
    body = issue_data.get("body", "")
    state = issue_data.get("state")

    # Check if we already have this issue
    existing = None
    for issue in graph.list_issues():
        if f"github:{github_id}" in issue.tags:
            existing = issue
            break

    if existing:
        # Update status
        if state == "closed":
            existing.status = IssueStatus.RESOLVED
        graph.save_issue(existing)

        return {
            "status": "updated",
            "issue_id": str(existing.id),
        }
    else:
        # Create new issue
        issue = Issue(
            title=f"[GitHub #{github_id}] {title}",
            description=body,
            severity=IssueSeverity.MEDIUM,
            status=IssueStatus.NEW if state == "open" else IssueStatus.RESOLVED,
            tags={f"github:{github_id}", "github"},
        )

        graph.save_issue(issue)

        return {
            "status": "created",
            "issue_id": str(issue.id),
        }


@router.get("/health")
async def webhook_health():
    """Webhook health check."""
    return {"status": "healthy", "service": "webhooks"}
