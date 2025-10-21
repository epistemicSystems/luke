"""Tests for developer actions."""

import pytest
import tempfile
from pathlib import Path

from insight_graph.core.graph import InsightGraph
from insight_graph.core.models import (
    User,
    Message,
    MessageLabel,
    IssueSeverity,
    IssueStatus,
)
from insight_graph.rag.actions import DevActions


@pytest.fixture
def graph_with_data():
    """Create a graph with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = InsightGraph(data_dir=Path(tmpdir))

        # Create user
        user = User(discord_id="123", discord_handle="TestUser")
        graph.save_user(user)

        # Create messages
        msg1 = Message(
            user_id=user.id,
            discord_message_id="m1",
            channel_id="c1",
            text="Game crashes",
            labels={MessageLabel.BUG_REPORT},
        )
        msg2 = Message(
            user_id=user.id,
            discord_message_id="m2",
            channel_id="c1",
            text="FPS drops",
            labels={MessageLabel.PERFORMANCE},
        )

        graph.save_message(msg1)
        graph.save_message(msg2)

        yield graph, user, [msg1, msg2]


def test_create_issue_from_messages(graph_with_data):
    """Test creating an issue from messages."""
    graph, user, messages = graph_with_data
    actions = DevActions(graph)

    issue = actions.create_issue_from_messages(
        title="Test Issue",
        description="Test description",
        message_ids=[msg.id for msg in messages],
        severity=IssueSeverity.HIGH,
        tags={"test"},
    )

    assert issue.title == "Test Issue"
    assert len(issue.linked_message_ids) == 2
    assert "test" in issue.tags

    # Check messages are linked back
    msg1 = graph.get_message(messages[0].id)
    assert issue.id in msg1.linked_issue_ids


def test_tag_message(graph_with_data):
    """Test tagging a message."""
    graph, user, messages = graph_with_data
    actions = DevActions(graph)

    actions.tag_message(messages[0].id, MessageLabel.CRASH)

    msg = graph.get_message(messages[0].id)
    assert MessageLabel.CRASH in msg.labels


def test_link_message_to_issue(graph_with_data):
    """Test linking a message to an issue."""
    graph, user, messages = graph_with_data
    actions = DevActions(graph)

    # Create issue
    issue = actions.create_issue_from_messages(
        title="Issue",
        description="Desc",
        message_ids=[],
        severity=IssueSeverity.MEDIUM,
    )

    # Link message
    actions.link_message_to_issue(messages[0].id, issue.id)

    # Check links
    msg = graph.get_message(messages[0].id)
    issue_updated = graph.get_issue(issue.id)

    assert issue.id in msg.linked_issue_ids
    assert messages[0].id in issue_updated.linked_message_ids


def test_update_issue_status(graph_with_data):
    """Test updating issue status."""
    graph, user, messages = graph_with_data
    actions = DevActions(graph)

    issue = actions.create_issue_from_messages(
        title="Issue",
        description="Desc",
        message_ids=[],
        severity=IssueSeverity.LOW,
    )

    # Update status
    actions.update_issue_status(issue.id, IssueStatus.IN_PROGRESS, owner="alice")

    updated = graph.get_issue(issue.id)
    assert updated.status == IssueStatus.IN_PROGRESS
    assert updated.owner_id == "alice"


def test_get_issue_bundle(graph_with_data):
    """Test getting issue bundles by tag."""
    graph, user, messages = graph_with_data
    actions = DevActions(graph)

    # Create issues with different tags
    issue1 = actions.create_issue_from_messages(
        title="Issue 1",
        description="D1",
        message_ids=[],
        severity=IssueSeverity.HIGH,
        tags={"performance"},
    )
    issue2 = actions.create_issue_from_messages(
        title="Issue 2",
        description="D2",
        message_ids=[],
        severity=IssueSeverity.MEDIUM,
        tags={"performance", "crash"},
    )
    issue3 = actions.create_issue_from_messages(
        title="Issue 3",
        description="D3",
        message_ids=[],
        severity=IssueSeverity.LOW,
        tags={"ui"},
    )

    bundle = actions.get_issue_bundle("performance", limit=10)
    assert len(bundle) == 2
    assert all("performance" in issue.tags for issue in bundle)
