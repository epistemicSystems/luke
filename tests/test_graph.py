"""Tests for graph operations."""

import pytest
import tempfile
from pathlib import Path

from insight_graph.core.graph import InsightGraph
from insight_graph.core.models import User, Message, Issue, IssueSeverity, IssueStatus


@pytest.fixture
def temp_graph():
    """Create a temporary graph for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = InsightGraph(data_dir=Path(tmpdir))
        yield graph


def test_save_and_retrieve_user(temp_graph):
    """Test saving and retrieving a user."""
    user = User(discord_id="123", discord_handle="TestUser")

    # Save
    temp_graph.save_user(user)

    # Retrieve
    retrieved = temp_graph.get_user(user.id)
    assert retrieved is not None
    assert retrieved.discord_id == "123"
    assert retrieved.discord_handle == "TestUser"


def test_get_user_by_discord_id(temp_graph):
    """Test retrieving user by Discord ID."""
    user = User(discord_id="456", discord_handle="DiscordUser")
    temp_graph.save_user(user)

    retrieved = temp_graph.get_user_by_discord_id("456")
    assert retrieved is not None
    assert retrieved.id == user.id


def test_list_users(temp_graph):
    """Test listing users."""
    user1 = User(discord_id="1", discord_handle="User1")
    user2 = User(discord_id="2", discord_handle="User2")

    temp_graph.save_user(user1)
    temp_graph.save_user(user2)

    users = temp_graph.list_users()
    assert len(users) == 2


def test_save_and_retrieve_message(temp_graph):
    """Test saving and retrieving a message."""
    user = User(discord_id="123", discord_handle="User")
    temp_graph.save_user(user)

    msg = Message(
        user_id=user.id,
        discord_message_id="msg_1",
        channel_id="channel_1",
        text="Test message",
    )

    temp_graph.save_message(msg)

    retrieved = temp_graph.get_message(msg.id)
    assert retrieved is not None
    assert retrieved.text == "Test message"
    assert retrieved.user_id == user.id


def test_save_and_retrieve_issue(temp_graph):
    """Test saving and retrieving an issue."""
    issue = Issue(
        title="Test Issue",
        description="A test issue",
        severity=IssueSeverity.HIGH,
        status=IssueStatus.NEW,
    )

    temp_graph.save_issue(issue)

    retrieved = temp_graph.get_issue(issue.id)
    assert retrieved is not None
    assert retrieved.title == "Test Issue"
    assert retrieved.severity == IssueSeverity.HIGH


def test_list_issues_by_status(temp_graph):
    """Test filtering issues by status."""
    issue1 = Issue(
        title="Issue 1",
        description="First",
        severity=IssueSeverity.HIGH,
        status=IssueStatus.NEW,
    )
    issue2 = Issue(
        title="Issue 2",
        description="Second",
        severity=IssueSeverity.MEDIUM,
        status=IssueStatus.TRIAGED,
    )

    temp_graph.save_issue(issue1)
    temp_graph.save_issue(issue2)

    new_issues = temp_graph.list_issues(status="new")
    assert len(new_issues) == 1
    assert new_issues[0].title == "Issue 1"


def test_version_log(temp_graph):
    """Test version logging."""
    user = User(discord_id="123", discord_handle="User")
    temp_graph.save_user(user)

    # Check log
    timeline = temp_graph.get_timeline(entity_type="users")
    assert len(timeline) > 0

    # Should have a create action
    creates = [e for e in timeline if e["action"] == "create"]
    assert len(creates) == 1
    assert creates[0]["entity_id"] == str(user.id)
