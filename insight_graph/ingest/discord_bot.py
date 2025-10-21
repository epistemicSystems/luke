"""
Discord bot for ingesting community messages.

Listens to configured channels and threads, normalizes messages,
and stores them in the Insight Graph + vector store.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

import discord
from discord.ext import commands
from dotenv import load_dotenv

from ..core.graph import InsightGraph
from ..core.models import Message, MessageLabel, Thread, User
from ..core.vector_store import VectorStore

load_dotenv()

logger = logging.getLogger(__name__)


class DiscordIngestBot(commands.Bot):
    """Discord bot that ingests messages into the Insight Graph."""

    def __init__(self, graph: InsightGraph, vector_store: VectorStore):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)

        self.graph = graph
        self.vector_store = vector_store

        # PII redaction patterns
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        self.ip_pattern = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Discord bot is starting up...")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")

    async def on_message(self, message: discord.Message) -> None:
        """
        Process incoming messages.

        Args:
            message: Discord message object
        """
        # Ignore bot messages
        if message.author.bot:
            return

        # Process the message
        await self.ingest_message(message)

        # Process commands (if any)
        await self.process_commands(message)

    async def ingest_message(self, discord_msg: discord.Message) -> UUID:
        """
        Ingest a Discord message into the graph.

        Args:
            discord_msg: Discord message object

        Returns:
            Message UUID
        """
        # Get or create user
        user = self.graph.get_user_by_discord_id(str(discord_msg.author.id))
        if not user:
            user = User(
                discord_id=str(discord_msg.author.id),
                discord_handle=discord_msg.author.name,
            )
            self.graph.save_user(user)
            logger.info(f"Created new user: {user.discord_handle}")

        # Clean text (PII redaction)
        text = discord_msg.content
        cleaned_text = self.redact_pii(text)

        # Extract media URLs
        media_urls = [attachment.url for attachment in discord_msg.attachments]

        # Create message
        msg = Message(
            user_id=user.id,
            discord_message_id=str(discord_msg.id),
            channel_id=str(discord_msg.channel.id),
            text=text,
            cleaned_text=cleaned_text,
            media_urls=media_urls,
        )

        # Auto-label based on content
        msg.labels = self.auto_label(cleaned_text)

        # Handle thread association
        if isinstance(discord_msg.channel, discord.Thread):
            thread = await self.get_or_create_thread(discord_msg.channel)
            msg.thread_id = thread.id

        # Handle replies
        if discord_msg.reference and discord_msg.reference.message_id:
            # Try to find the parent message in our graph
            # (simplified: assumes we've seen the parent)
            pass

        # Save to graph
        self.graph.save_message(msg)

        # Add to vector store
        metadata = {
            "user_id": str(user.id),
            "channel_id": str(discord_msg.channel.id),
            "labels": [label.value for label in msg.labels],
            "created_at": msg.created_at.isoformat(),
        }

        embedding_id = self.vector_store.add_message(
            message_id=msg.id,
            text=cleaned_text,
            metadata=metadata,
        )

        msg.embedding_id = embedding_id
        self.graph.save_message(msg)

        logger.info(
            f"Ingested message {msg.id} from {user.discord_handle} in #{discord_msg.channel.name}"
        )

        return msg.id

    async def get_or_create_thread(self, discord_thread: discord.Thread) -> Thread:
        """
        Get or create a thread in the graph.

        Args:
            discord_thread: Discord thread object

        Returns:
            Thread object
        """
        # Try to find existing thread
        for thread in self.graph.list_threads(channel_id=str(discord_thread.parent_id)):
            if thread.discord_thread_id == str(discord_thread.id):
                return thread

        # Create new thread
        thread = Thread(
            channel_id=str(discord_thread.parent_id),
            discord_thread_id=str(discord_thread.id),
            title=discord_thread.name,
        )

        self.graph.save_thread(thread)
        logger.info(f"Created new thread: {thread.title}")

        return thread

    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text.

        Args:
            text: Input text

        Returns:
            Text with PII redacted
        """
        # Redact emails
        text = self.email_pattern.sub("[EMAIL]", text)

        # Redact IPs
        text = self.ip_pattern.sub("[IP]", text)

        return text

    def auto_label(self, text: str) -> set[MessageLabel]:
        """
        Auto-label messages based on content patterns.

        Args:
            text: Message text

        Returns:
            Set of labels
        """
        labels = set()
        text_lower = text.lower()

        # Bug indicators
        bug_keywords = ["bug", "broken", "crash", "error", "issue", "not working", "doesn't work"]
        if any(keyword in text_lower for keyword in bug_keywords):
            labels.add(MessageLabel.BUG_REPORT)

        # Performance indicators
        perf_keywords = ["fps", "lag", "slow", "stutter", "freeze", "performance"]
        if any(keyword in text_lower for keyword in perf_keywords):
            labels.add(MessageLabel.PERFORMANCE)

        # Crash indicators
        if "crash" in text_lower or "crashed" in text_lower:
            labels.add(MessageLabel.CRASH)

        # Feature request indicators
        feature_keywords = ["feature", "request", "would be nice", "could you add", "suggestion"]
        if any(keyword in text_lower for keyword in feature_keywords):
            labels.add(MessageLabel.FEATURE_REQUEST)

        # Question indicators
        question_keywords = ["how", "what", "where", "when", "why", "?"]
        if any(keyword in text_lower for keyword in question_keywords):
            labels.add(MessageLabel.QUESTION)

        # Praise indicators
        praise_keywords = ["love", "great", "awesome", "amazing", "thank", "appreciate"]
        if any(keyword in text_lower for keyword in praise_keywords):
            labels.add(MessageLabel.PRAISE)

        # Complaint indicators (without bug context)
        complaint_keywords = ["hate", "annoying", "frustrat", "terrible", "awful"]
        if any(keyword in text_lower for keyword in complaint_keywords):
            if MessageLabel.BUG_REPORT not in labels:
                labels.add(MessageLabel.COMPLAINT)

        return labels


async def main():
    """Main entry point for the Discord bot."""
    # Load environment
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN not set in environment")

    graph_data_dir = os.getenv("GRAPH_DATA_DIR", "./data/graph")
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    chroma_collection = os.getenv("CHROMA_COLLECTION", "insight_graph")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")

    # Initialize graph and vector store
    graph = InsightGraph(data_dir=Path(graph_data_dir))
    vector_store = VectorStore(
        persist_dir=chroma_persist_dir,
        collection_name=chroma_collection,
        openai_api_key=openai_api_key,
    )

    # Create and run bot
    bot = DiscordIngestBot(graph=graph, vector_store=vector_store)

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())
