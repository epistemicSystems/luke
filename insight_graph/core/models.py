"""
Core data models for the Insight Graph.

These models represent the fundamental objects in our knowledge graph,
versioned Git-style for audit and rollback.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CapabilityBand(str, Enum):
    """Hardware/capability classifications (privacy-safe)."""

    LOW_VRAM = "low-vram"
    MID_VRAM = "mid-vram"
    HIGH_VRAM = "high-vram"
    LOW_CPU = "low-cpu"
    MID_CPU = "mid-cpu"
    HIGH_CPU = "high-cpu"
    CONTROLLER = "controller"
    KB_MOUSE = "kb-mouse"
    LOW_BANDWIDTH = "low-bandwidth"
    HIGH_BANDWIDTH = "high-bandwidth"


class PlaystyleSignal(str, Enum):
    """Behavioral patterns (inferred, not declared)."""

    EXPLORER = "explorer"
    COMPLETIONIST = "completionist"
    COMPETITIVE = "competitive"
    SOCIAL = "social"
    CASUAL = "casual"
    HARDCORE = "hardcore"


class User(BaseModel):
    """Community member with capability bands and playstyle signals."""

    id: UUID = Field(default_factory=uuid4)
    discord_id: str
    discord_handle: str

    # Privacy-safe capability bands (opt-in)
    capability_bands: set[CapabilityBand] = Field(default_factory=set)

    # Inferred behavioral signals (not PII)
    playstyle_signals: set[PlaystyleSignal] = Field(default_factory=set)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    opted_in: bool = False  # Explicit consent for telemetry

    # Graph linkage
    message_ids: list[UUID] = Field(default_factory=list)
    thread_ids: list[UUID] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "discord_id": "123456789",
                "discord_handle": "Ravenwood#1234",
                "capability_bands": ["low-vram", "controller"],
                "playstyle_signals": ["explorer", "completionist"],
                "opted_in": True,
            }
        }


class MessageLabel(str, Enum):
    """Semantic labels for messages."""

    BUG_REPORT = "bug-report"
    FEATURE_REQUEST = "feature-request"
    PRAISE = "praise"
    COMPLAINT = "complaint"
    QUESTION = "question"
    REPRO_STEPS = "repro-steps"
    WORKAROUND = "workaround"
    CRASH = "crash"
    PERFORMANCE = "performance"
    UX_CONFUSION = "ux-confusion"


class Message(BaseModel):
    """Discord message with embeddings and labels."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    discord_message_id: str
    channel_id: str
    thread_id: Optional[UUID] = None

    # Content
    text: str
    cleaned_text: Optional[str] = None  # After PII redaction
    media_urls: list[str] = Field(default_factory=list)

    # Embeddings (stored separately in vector DB, referenced here)
    embedding_id: Optional[str] = None

    # Labels
    labels: set[MessageLabel] = Field(default_factory=set)
    topic_tags: list[str] = Field(default_factory=list)

    # Sentiment analysis
    sentiment_score: Optional[float] = None  # -1.0 (negative) to 1.0 (positive)
    frustration_score: Optional[float] = None  # 0.0 to 1.0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None

    # Graph linkage
    reply_to_id: Optional[UUID] = None
    mentions_user_ids: list[UUID] = Field(default_factory=list)
    linked_issue_ids: list[UUID] = Field(default_factory=list)


class Thread(BaseModel):
    """Conversation thread with topic labels and sentiment timeline."""

    id: UUID = Field(default_factory=uuid4)
    channel_id: str
    discord_thread_id: Optional[str] = None

    # Content
    title: Optional[str] = None
    message_ids: list[UUID] = Field(default_factory=list)

    # Classification
    topic_labels: list[str] = Field(default_factory=list)
    primary_label: Optional[MessageLabel] = None

    # Analytics
    sentiment_timeseries: list[tuple[datetime, float]] = Field(default_factory=list)
    participant_ids: set[UUID] = Field(default_factory=set)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Graph linkage
    linked_issue_ids: list[UUID] = Field(default_factory=list)


class IssueSeverity(str, Enum):
    """Issue severity classification."""

    CRITICAL = "critical"  # Game-breaking, crashes
    HIGH = "high"  # Major functionality broken
    MEDIUM = "medium"  # Annoying but workable
    LOW = "low"  # Polish, nice-to-have


class IssueStatus(str, Enum):
    """Issue lifecycle status."""

    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    WONT_FIX = "wont-fix"
    DUPLICATE = "duplicate"


class Issue(BaseModel):
    """Bug or feature request with repro steps and linkage."""

    id: UUID = Field(default_factory=uuid4)

    # Core fields
    title: str
    description: str
    steps_to_repro: list[str] = Field(default_factory=list)
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None

    # Classification
    severity: IssueSeverity
    status: IssueStatus = IssueStatus.NEW
    tags: set[str] = Field(default_factory=set)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    owner_id: Optional[str] = None  # Dev assigned

    # Graph linkage
    linked_thread_ids: list[UUID] = Field(default_factory=list)
    linked_message_ids: list[UUID] = Field(default_factory=list)
    build_id: Optional[UUID] = None
    duplicate_of: Optional[UUID] = None

    # Impact forecasting
    affected_persona_ids: list[UUID] = Field(default_factory=list)
    impact_scores: dict[str, float] = Field(default_factory=dict)  # persona_id -> score


class Build(BaseModel):
    """Game build/release with changelog and feature flags."""

    id: UUID = Field(default_factory=uuid4)

    # Version info
    version: str  # e.g., "0.9.3"
    branch: str
    commit_sha: Optional[str] = None

    # Release notes
    changelog: str
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    rollout_segment: Optional[str] = None  # e.g., "beta-testers-cohort-a"

    # Metadata
    released_at: datetime = Field(default_factory=datetime.utcnow)

    # Graph linkage
    resolved_issue_ids: list[UUID] = Field(default_factory=list)
    introduced_issue_ids: list[UUID] = Field(default_factory=list)


class Persona(BaseModel):
    """
    Archetypal user basis extracted via spectral analysis.
    Each persona can be instantiated as an interactive LLM agent.
    """

    id: UUID = Field(default_factory=uuid4)

    # Core identity
    name: str  # e.g., "Low-VRAM Explorer"
    description: str

    # Basis weights (from spectral/NMF decomposition)
    basis_weights: dict[str, float] = Field(default_factory=dict)
    # e.g., {"topic:performance": 0.7, "biome:swamp": 0.5, "control:controller": 0.2}

    # Examples and patterns
    canonical_examples: list[UUID] = Field(default_factory=list)  # Representative message IDs
    pain_points: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)

    # LLM agent profile (loaded from YAML)
    prompt_profile_path: Optional[str] = None

    # Evaluation metrics
    coverage: float = 0.0  # % of users with high match
    stability: float = 0.0  # Jaccard of top-k week-to-week

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Graph linkage
    representative_user_ids: list[UUID] = Field(default_factory=list)


class Insight(BaseModel):
    """Hypothesis or key finding with evidence and confidence."""

    id: UUID = Field(default_factory=uuid4)

    # Core content
    hypothesis: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    # e.g., [{"type": "message", "id": uuid}, {"type": "thread", "id": uuid}]

    confidence: float  # 0.0 to 1.0

    # Metadata
    author: str  # Could be "system" or a dev username
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: set[str] = Field(default_factory=set)


class Decision(BaseModel):
    """Design decision with context, rationale, and expected impact."""

    id: UUID = Field(default_factory=uuid4)

    # Core content
    context_refs: list[dict[str, Any]] = Field(default_factory=list)
    chosen_option: str
    alternatives_considered: list[str] = Field(default_factory=list)
    rationale: str

    # Impact forecasting
    expected_impact_by_persona: dict[UUID, dict[str, Any]] = Field(default_factory=dict)
    # e.g., {persona_id: {"risk_score": 0.3, "opportunity_score": 0.7, "notes": "..."}}

    # Metadata
    author: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Linkage
    related_issue_ids: list[UUID] = Field(default_factory=list)
    related_build_id: Optional[UUID] = None
