"""
Slack integration for posting briefs and notifications.

Posts daily briefs and alerts to Slack channels.
"""

import os
from typing import Optional

import aiohttp


class SlackNotifier:
    """
    Send messages to Slack via webhook.

    Usage:
        notifier = SlackNotifier(webhook_url)
        await notifier.post_brief(brief_text)
        await notifier.post_alert("High-severity issue detected!")
    """

    def __init__(self, webhook_url: str):
        """
        Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL (from Slack app settings)
        """
        self.webhook_url = webhook_url

    async def post_message(
        self,
        text: str,
        channel: Optional[str] = None,
        username: str = "Insight Graph",
        icon_emoji: str = ":chart_with_upwards_trend:",
    ) -> bool:
        """
        Post a message to Slack.

        Args:
            text: Message text (markdown supported)
            channel: Optional channel override
            username: Bot username
            icon_emoji: Bot icon

        Returns:
            True if successful
        """
        payload = {
            "text": text,
            "username": username,
            "icon_emoji": icon_emoji,
        }

        if channel:
            payload["channel"] = channel

        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=payload) as response:
                return response.status == 200

    async def post_brief(self, brief_text: str, channel: Optional[str] = None) -> bool:
        """
        Post a daily brief to Slack.

        Args:
            brief_text: Formatted brief text
            channel: Optional channel override

        Returns:
            True if successful
        """
        return await self.post_message(
            text=brief_text,
            channel=channel,
            username="Insight Graph Brief",
            icon_emoji=":newspaper:",
        )

    async def post_alert(
        self,
        title: str,
        message: str,
        severity: str = "high",
        channel: Optional[str] = None,
    ) -> bool:
        """
        Post an alert to Slack.

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity (low, medium, high, critical)
            channel: Optional channel override

        Returns:
            True if successful
        """
        emoji_map = {
            "low": ":information_source:",
            "medium": ":warning:",
            "high": ":rotating_light:",
            "critical": ":fire:",
        }

        icon = emoji_map.get(severity, ":warning:")

        formatted = f"{icon} *{title}*\n{message}"

        return await self.post_message(
            text=formatted,
            channel=channel,
            username="Insight Graph Alert",
            icon_emoji=icon,
        )

    async def post_issue_created(
        self,
        issue_title: str,
        issue_id: str,
        severity: str,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Post notification when issue is created.

        Args:
            issue_title: Issue title
            issue_id: Issue UUID
            severity: Issue severity
            channel: Optional channel override

        Returns:
            True if successful
        """
        message = f":bug: *New Issue Created*\n*{issue_title}*\nSeverity: {severity}\nID: `{issue_id}`"

        return await self.post_message(text=message, channel=channel)


# Sync wrapper for non-async contexts
class SlackNotifierSync:
    """Synchronous wrapper for SlackNotifier."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def post_message(
        self,
        text: str,
        channel: Optional[str] = None,
        username: str = "Insight Graph",
        icon_emoji: str = ":chart_with_upwards_trend:",
    ) -> bool:
        """Post a message to Slack (sync)."""
        import asyncio

        notifier = SlackNotifier(self.webhook_url)
        return asyncio.run(notifier.post_message(text, channel, username, icon_emoji))

    def post_brief(self, brief_text: str, channel: Optional[str] = None) -> bool:
        """Post a brief to Slack (sync)."""
        import asyncio

        notifier = SlackNotifier(self.webhook_url)
        return asyncio.run(notifier.post_brief(brief_text, channel))

    def post_alert(
        self,
        title: str,
        message: str,
        severity: str = "high",
        channel: Optional[str] = None,
    ) -> bool:
        """Post an alert to Slack (sync)."""
        import asyncio

        notifier = SlackNotifier(self.webhook_url)
        return asyncio.run(notifier.post_alert(title, message, severity, channel))


# CLI for testing
async def main():
    """Test Slack notifications."""
    import sys

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL not set")
        sys.exit(1)

    notifier = SlackNotifier(webhook_url)

    # Test message
    success = await notifier.post_message("Test message from Insight Graph!")

    if success:
        print("✓ Message posted successfully")
    else:
        print("✗ Failed to post message")

    # Test alert
    success = await notifier.post_alert(
        title="High Sentiment Detected",
        message="Community sentiment has dropped below -0.5",
        severity="high",
    )

    if success:
        print("✓ Alert posted successfully")
    else:
        print("✗ Failed to post alert")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
