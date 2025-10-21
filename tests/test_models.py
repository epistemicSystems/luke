"""Tests for core data models."""

import pytest
from datetime import datetime

from insight_graph.core.models import (
    User,
    Message,
    Issue,
    Persona,
    CapabilityBand,
    PlaystyleSignal,
    MessageLabel,
    IssueSeverity,
    IssueStatus,
)


def test_user_creation():
    """Test user creation and validation."""
    user = User(
        discord_id="123456",
        discord_handle="TestUser",
        capability_bands={CapabilityBand.LOW_VRAM, CapabilityBand.CONTROLLER},
        playstyle_signals={PlaystyleSignal.CASUAL},
    )

    assert user.discord_id == "123456"
    assert user.discord_handle == "TestUser"
    assert CapabilityBand.LOW_VRAM in user.capability_bands
    assert PlaystyleSignal.CASUAL in user.playstyle_signals
    assert user.id is not None


def test_message_creation():
    """Test message creation and labeling."""
    user = User(discord_id="123", discord_handle="User")

    msg = Message(
        user_id=user.id,
        discord_message_id="msg_123",
        channel_id="channel_1",
        text="Game crashes when entering forest",
        labels={MessageLabel.BUG_REPORT, MessageLabel.CRASH},
    )

    assert msg.user_id == user.id
    assert MessageLabel.BUG_REPORT in msg.labels
    assert MessageLabel.CRASH in msg.labels


def test_issue_creation():
    """Test issue creation."""
    issue = Issue(
        title="Crash in forest biome",
        description="Multiple reports of crashes",
        severity=IssueSeverity.CRITICAL,
        status=IssueStatus.NEW,
        tags={"crash", "forest"},
    )

    assert issue.title == "Crash in forest biome"
    assert issue.severity == IssueSeverity.CRITICAL
    assert issue.status == IssueStatus.NEW
    assert "crash" in issue.tags


def test_persona_creation():
    """Test persona creation."""
    persona = Persona(
        name="Test Persona",
        description="A test persona",
        pain_points=["performance", "controls"],
        goals=["smooth_gameplay", "accessibility"],
    )

    assert persona.name == "Test Persona"
    assert "performance" in persona.pain_points
    assert "smooth_gameplay" in persona.goals


def test_model_serialization():
    """Test model JSON serialization."""
    user = User(discord_id="123", discord_handle="Test")

    # Serialize
    json_data = user.model_dump_json()
    assert "discord_id" in json_data
    assert "123" in json_data

    # Deserialize
    user2 = User.model_validate_json(json_data)
    assert user2.discord_id == user.discord_id
    assert user2.id == user.id
