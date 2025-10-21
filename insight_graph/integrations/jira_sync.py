"""
JIRA integration for bi-directional issue sync.

Syncs issues between Insight Graph and JIRA.
"""

import os
from typing import Optional
from uuid import UUID

from jira import JIRA

from ..core.graph import InsightGraph
from ..core.models import Issue, IssueSeverity, IssueStatus


class JIRAIntegration:
    """
    JIRA integration for issue sync.

    Usage:
        jira = JIRAIntegration(
            server="https://your-domain.atlassian.net",
            email="your@email.com",
            api_token="your_token"
        )

        # Export issues to JIRA
        jira.export_issues(graph, project_key="GAME")

        # Import from JIRA
        jira.import_issues(graph, project_key="GAME")
    """

    def __init__(self, server: str, email: str, api_token: str):
        """
        Initialize JIRA client.

        Args:
            server: JIRA server URL
            email: Account email
            api_token: API token (from Atlassian account settings)
        """
        self.client = JIRA(server=server, basic_auth=(email, api_token))

    def export_issue(
        self,
        graph: InsightGraph,
        issue_id: UUID,
        project_key: str,
        issue_type: str = "Bug",
    ) -> Optional[str]:
        """
        Export a single issue to JIRA.

        Args:
            graph: Insight graph
            issue_id: Issue UUID
            project_key: JIRA project key
            issue_type: JIRA issue type

        Returns:
            JIRA issue key (e.g., "GAME-123") or None if failed
        """
        issue = graph.get_issue(issue_id)
        if not issue:
            return None

        # Check if already exported
        for tag in issue.tags:
            if tag.startswith("jira:"):
                jira_key = tag.replace("jira:", "")
                print(f"Issue already exported: {jira_key}")
                return jira_key

        # Map severity to priority
        priority_map = {
            IssueSeverity.CRITICAL: "Highest",
            IssueSeverity.HIGH: "High",
            IssueSeverity.MEDIUM: "Medium",
            IssueSeverity.LOW: "Low",
        }

        priority = priority_map.get(issue.severity, "Medium")

        # Create JIRA issue
        jira_issue = self.client.create_issue(
            project=project_key,
            summary=issue.title,
            description=self._format_description(issue),
            issuetype={"name": issue_type},
            priority={"name": priority},
        )

        # Tag with JIRA key
        issue.tags.add(f"jira:{jira_issue.key}")
        graph.save_issue(issue)

        print(f"Created JIRA issue: {jira_issue.key}")
        return jira_issue.key

    def export_issues(
        self,
        graph: InsightGraph,
        project_key: str,
        status: Optional[str] = None,
    ) -> list[str]:
        """
        Export multiple issues to JIRA.

        Args:
            graph: Insight graph
            project_key: JIRA project key
            status: Optional status filter

        Returns:
            List of created JIRA keys
        """
        issues = graph.list_issues(status=status)
        jira_keys = []

        for issue in issues:
            jira_key = self.export_issue(graph, issue.id, project_key)
            if jira_key:
                jira_keys.append(jira_key)

        return jira_keys

    def import_issues(
        self,
        graph: InsightGraph,
        project_key: str,
        jql: Optional[str] = None,
    ) -> list[UUID]:
        """
        Import issues from JIRA.

        Args:
            graph: Insight graph
            project_key: JIRA project key
            jql: Optional JQL query (defaults to all open issues)

        Returns:
            List of created issue UUIDs
        """
        if not jql:
            jql = f'project = {project_key} AND status != "Done"'

        jira_issues = self.client.search_issues(jql)
        issue_ids = []

        for jira_issue in jira_issues:
            # Check if already imported
            existing = None
            for issue in graph.list_issues():
                if f"jira:{jira_issue.key}" in issue.tags:
                    existing = issue
                    break

            if existing:
                # Update status
                existing = self._update_from_jira(existing, jira_issue)
                graph.save_issue(existing)
                issue_ids.append(existing.id)
            else:
                # Create new
                issue = self._create_from_jira(jira_issue)
                graph.save_issue(issue)
                issue_ids.append(issue.id)

        return issue_ids

    def sync_status(self, graph: InsightGraph, issue_id: UUID) -> bool:
        """
        Sync issue status with JIRA.

        Args:
            graph: Insight graph
            issue_id: Issue UUID

        Returns:
            True if successful
        """
        issue = graph.get_issue(issue_id)
        if not issue:
            return False

        # Find JIRA key
        jira_key = None
        for tag in issue.tags:
            if tag.startswith("jira:"):
                jira_key = tag.replace("jira:", "")
                break

        if not jira_key:
            return False

        # Get JIRA issue
        jira_issue = self.client.issue(jira_key)

        # Update from JIRA
        issue = self._update_from_jira(issue, jira_issue)
        graph.save_issue(issue)

        return True

    def _format_description(self, issue: Issue) -> str:
        """Format issue description for JIRA."""
        parts = [issue.description]

        if issue.steps_to_repro:
            parts.append("\n\n*Steps to Reproduce:*")
            for i, step in enumerate(issue.steps_to_repro, 1):
                parts.append(f"{i}. {step}")

        if issue.tags:
            parts.append(f"\n\n*Tags:* {', '.join(issue.tags)}")

        parts.append(f"\n\n_Imported from Insight Graph (ID: {issue.id})_")

        return "\n".join(parts)

    def _create_from_jira(self, jira_issue: Any) -> Issue:
        """Create Issue from JIRA issue."""
        # Map priority to severity
        priority = jira_issue.fields.priority.name if jira_issue.fields.priority else "Medium"
        severity_map = {
            "Highest": IssueSeverity.CRITICAL,
            "High": IssueSeverity.HIGH,
            "Medium": IssueSeverity.MEDIUM,
            "Low": IssueSeverity.LOW,
        }
        severity = severity_map.get(priority, IssueSeverity.MEDIUM)

        # Map status
        status = jira_issue.fields.status.name
        status_map = {
            "Open": IssueStatus.NEW,
            "In Progress": IssueStatus.IN_PROGRESS,
            "Done": IssueStatus.RESOLVED,
            "Closed": IssueStatus.RESOLVED,
        }
        issue_status = status_map.get(status, IssueStatus.NEW)

        return Issue(
            title=f"[JIRA-{jira_issue.key}] {jira_issue.fields.summary}",
            description=jira_issue.fields.description or "",
            severity=severity,
            status=issue_status,
            tags={f"jira:{jira_issue.key}", "jira"},
        )

    def _update_from_jira(self, issue: Issue, jira_issue: Any) -> Issue:
        """Update Issue from JIRA issue."""
        # Update status
        status = jira_issue.fields.status.name
        status_map = {
            "Open": IssueStatus.NEW,
            "In Progress": IssueStatus.IN_PROGRESS,
            "Done": IssueStatus.RESOLVED,
            "Closed": IssueStatus.RESOLVED,
        }
        issue.status = status_map.get(status, issue.status)

        return issue


# CLI for testing
def main():
    """Test JIRA integration."""
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    jira_server = os.getenv("JIRA_SERVER")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_server, jira_email, jira_token]):
        print("Error: JIRA credentials not set in .env")
        sys.exit(1)

    graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
    graph = InsightGraph(data_dir=graph_data_dir)

    jira = JIRAIntegration(jira_server, jira_email, jira_token)

    # Test export
    print("Exporting issues to JIRA...")
    jira_keys = jira.export_issues(graph, project_key="GAME", status="triaged")
    print(f"Exported {len(jira_keys)} issues: {jira_keys}")

    # Test import
    print("\nImporting issues from JIRA...")
    issue_ids = jira.import_issues(graph, project_key="GAME")
    print(f"Imported {len(issue_ids)} issues")


if __name__ == "__main__":
    main()
