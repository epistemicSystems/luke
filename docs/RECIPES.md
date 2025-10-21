# Workflow Recipes

Real-world workflows and recipes for common use cases.

## Daily Operations

### Recipe 1: Morning Standup Automation

**Goal**: Automatically generate and post a daily brief to Slack at 9 AM.

```bash
#!/bin/bash
# scripts/daily_standup.sh

# Generate brief
python -m insight_graph.briefs.daily --hours 24 --format slack > /tmp/brief.txt

# Post to Slack
python -c "
from insight_graph.integrations.slack import SlackNotifierSync
import os

notifier = SlackNotifierSync(os.getenv('SLACK_WEBHOOK_URL'))
brief = open('/tmp/brief.txt').read()
notifier.post_brief(brief, channel='#dev-standup')
print('Posted daily brief to Slack')
"
```

**Cron setup**:
```cron
0 9 * * 1-5 /path/to/scripts/daily_standup.sh
```

### Recipe 2: Real-time Sentiment Monitoring

**Goal**: Alert when community sentiment drops below threshold.

```python
# scripts/sentiment_monitor.py

import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from insight_graph.core.graph import InsightGraph
from insight_graph.integrations.slack import SlackNotifierSync
from insight_graph.understand.sentiment import SentimentAnalyzer

load_dotenv()

# Initialize
graph = InsightGraph(Path(os.getenv("GRAPH_DATA_DIR")))
analyzer = SentimentAnalyzer(graph)
slack = SlackNotifierSync(os.getenv("SLACK_WEBHOOK_URL"))

# Get recent messages (last hour)
since = datetime.utcnow() - timedelta(hours=1)
messages = [m for m in graph.list_messages(limit=1000) if m.created_at >= since]

# Analyze
trend = analyzer.get_sentiment_trend(messages)

# Alert if negative
if trend["avg_sentiment"] < -0.5 or trend["avg_frustration"] > 0.7:
    slack.post_alert(
        title="⚠️ Community Sentiment Alert",
        message=f"Sentiment: {trend['avg_sentiment']:.2f}\n"
        f"Frustration: {trend['avg_frustration']:.2f}\n"
        f"Messages: {trend['count']}",
        severity="high",
        channel="#dev-alerts",
    )
```

**Run every hour**:
```cron
0 * * * * python /path/to/scripts/sentiment_monitor.py
```

## Issue Management

### Recipe 3: Auto-Triage New Issues

**Goal**: Automatically classify and assign issues based on labels and personas.

```python
# scripts/auto_triage.py

from pathlib import Path
from insight_graph.core.graph import InsightGraph
from insight_graph.personas.agents import PersonaAgent
from insight_graph.rag.actions import DevActions

graph = InsightGraph(Path("./data/graph"))
actions = DevActions(graph)

# Get new issues
new_issues = graph.list_issues(status="new")

for issue in new_issues:
    # Score impact across personas
    scores = {}
    for persona_file in Path("./insight_graph/personas/profiles").glob("*.yaml"):
        agent = PersonaAgent(persona_file, graph, None)
        score = agent.score_impact(list(issue.tags))
        scores[agent.persona_id] = score

    # Find most affected persona
    top_persona = max(scores, key=scores.get)
    top_score = scores[top_persona]

    # Auto-assign priority based on score
    if top_score > 0.8:
        severity = "high"
        owner = "team-lead"
    elif top_score > 0.5:
        severity = "medium"
        owner = "on-call"
    else:
        severity = "low"
        owner = None

    # Update issue
    issue.tags.add(f"persona:{top_persona}")
    issue.tags.add(f"auto-triaged")

    if owner:
        from insight_graph.core.models import IssueStatus
        actions.update_issue_status(issue.id, IssueStatus.TRIAGED, owner=owner)

    print(f"Triaged {issue.title}: {severity} → {owner or 'unassigned'}")
```

### Recipe 4: Weekly Issue Digest

**Goal**: Generate a weekly rollup of all issue activity.

```bash
# Generate weekly digest
python -m insight_graph.briefs.daily --hours 168 --format discord > weekly_digest.txt

# Add issue breakdown
python -c "
from insight_graph.core.graph import InsightGraph
from pathlib import Path

graph = InsightGraph(Path('./data/graph'))
issues = graph.list_issues()

by_status = {}
for issue in issues:
    status = issue.status.value
    by_status[status] = by_status.get(status, 0) + 1

print('\n\n## Issue Breakdown')
for status, count in sorted(by_status.items()):
    print(f'- {status}: {count}')
" >> weekly_digest.txt

# Send to team
cat weekly_digest.txt | mail -s "Weekly Insight Graph Digest" team@example.com
```

## Persona Analysis

### Recipe 5: Persona Coverage Report

**Goal**: Understand which personas are active and their pain points.

```python
# scripts/persona_coverage.py

from pathlib import Path
from insight_graph.core.graph import InsightGraph
from insight_graph.understand.clustering import UserClusterer
from insight_graph.core.vector_store import VectorStore
import os

graph = InsightGraph(Path("./data/graph"))
vector_store = VectorStore(
    persist_dir="./data/chroma",
    collection_name="insight_graph",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

# Cluster users
clusterer = UserClusterer(graph, vector_store)
users = graph.list_users()

result = clusterer.cluster_users(users, n_clusters=4)

print("=== Persona Coverage Report ===\n")

for cluster in result["clusters"]:
    print(f"Cluster {cluster['cluster_id']}: {cluster['size']} users ({cluster['size']/len(users)*100:.1f}%)")
    print(f"  Top capabilities: {', '.join(cluster['top_capabilities'])}")
    print(f"  Top playstyles: {', '.join(cluster['top_playstyles'])}")
    print(f"  Sample: {', '.join(cluster['sample_handles'][:3])}")
    print()

# Get pain points by cluster
personas = graph.list_personas()
issues = graph.list_issues()

print("=== Top Issues by Persona ===\n")

for persona in personas:
    affected_issues = [i for i in issues if persona.id in i.affected_persona_ids]
    print(f"{persona.name}: {len(affected_issues)} issues")

    if affected_issues:
        top_3 = sorted(affected_issues, key=lambda i: i.severity.value, reverse=True)[:3]
        for issue in top_3:
            print(f"  - [{issue.severity.value}] {issue.title}")
    print()
```

### Recipe 6: Impact Forecasting for PRs

**Goal**: Run persona simulations before merging PRs.

```bash
#!/bin/bash
# scripts/pr_impact_check.sh
# Run this as a GitHub Action or git hook

PR_TITLE="$1"
PR_DESCRIPTION="$2"

echo "=== Running Persona Impact Simulation ==="
echo "PR: $PR_TITLE"
echo ""

# Simulate impact
python -c "
from insight_graph.personas.agents import PersonaSimulator
from insight_graph.core.graph import InsightGraph
from insight_graph.core.vector_store import VectorStore
from pathlib import Path
import os

graph = InsightGraph(Path('./data/graph'))
vector_store = VectorStore(
    persist_dir='./data/chroma',
    collection_name='insight_graph',
    openai_api_key=os.getenv('OPENAI_API_KEY'),
)

simulator = PersonaSimulator(
    graph,
    vector_store,
    Path('./insight_graph/personas/profiles')
)

result = simulator.simulate_change('$PR_DESCRIPTION')

print(result['summary'])
" > impact_report.txt

# Post as PR comment (via GitHub CLI)
gh pr comment --body-file impact_report.txt
```

## Integration Workflows

### Recipe 7: Bi-directional JIRA Sync

**Goal**: Keep JIRA and Insight Graph in sync.

```python
# scripts/jira_sync_bidirectional.py

import os
from pathlib import Path
from insight_graph.core.graph import InsightGraph
from insight_graph.integrations.jira_sync import JIRAIntegration

graph = InsightGraph(Path("./data/graph"))

jira = JIRAIntegration(
    server=os.getenv("JIRA_SERVER"),
    email=os.getenv("JIRA_EMAIL"),
    api_token=os.getenv("JIRA_API_TOKEN"),
)

# Export new triaged issues to JIRA
triaged = graph.list_issues(status="triaged")
unsynced = [i for i in triaged if not any(t.startswith("jira:") for t in i.tags)]

print(f"Exporting {len(unsynced)} issues to JIRA...")
jira_keys = []
for issue in unsynced:
    key = jira.export_issue(graph, issue.id, project_key="GAME")
    if key:
        jira_keys.append(key)

print(f"Exported: {', '.join(jira_keys)}")

# Import updates from JIRA
print("\nImporting updates from JIRA...")
issue_ids = jira.import_issues(graph, project_key="GAME")
print(f"Synced {len(issue_ids)} issues from JIRA")

# Sync status for all linked issues
print("\nSyncing status for linked issues...")
all_issues = graph.list_issues()
for issue in all_issues:
    if any(t.startswith("jira:") for t in issue.tags):
        jira.sync_status(graph, issue.id)

print("Sync complete!")
```

**Run every 30 minutes**:
```cron
*/30 * * * * python /path/to/scripts/jira_sync_bidirectional.py
```

### Recipe 8: Discord → Slack Bridge

**Goal**: Mirror critical Discord messages to Slack.

```python
# Add to insight_graph/ingest/discord_bot.py

from ..integrations.slack import SlackNotifierSync

class DiscordIngestBot(commands.Bot):
    def __init__(self, graph, vector_store):
        super().__init__(...)
        self.slack = SlackNotifierSync(os.getenv("SLACK_WEBHOOK_URL"))

    async def ingest_message(self, discord_msg):
        msg_id = await super().ingest_message(discord_msg)

        msg = self.graph.get_message(msg_id)

        # Mirror high-severity issues to Slack
        if MessageLabel.CRASH in msg.labels or MessageLabel.CRITICAL in msg.labels:
            self.slack.post_alert(
                title=f"Critical Issue from Discord",
                message=f"User: {discord_msg.author.name}\n"
                        f"Channel: #{discord_msg.channel.name}\n"
                        f"Message: {msg.text[:200]}",
                severity="critical",
                channel="#critical-issues",
            )

        return msg_id
```

## Advanced Analytics

### Recipe 9: Automatic Persona Discovery

**Goal**: Run weekly persona extraction to discover new segments.

```python
# scripts/discover_personas.py

from pathlib import Path
from insight_graph.core.graph import InsightGraph
from insight_graph.core.vector_store import VectorStore
from insight_graph.understand.clustering import UserClusterer
import os

graph = InsightGraph(Path("./data/graph"))
vector_store = VectorStore(
    persist_dir="./data/chroma",
    collection_name="insight_graph",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

users = graph.list_users()
print(f"Analyzing {len(users)} users for persona discovery...\n")

clusterer = UserClusterer(graph, vector_store)

# Extract persona bases via NMF
result = clusterer.extract_persona_bases_nmf(users, n_components=6)

print("=== Discovered Persona Bases ===\n")

for basis in result["bases"]:
    print(f"Basis {basis['basis_id']}:")

    # Top features
    for feature, weight in basis["top_features"][:5]:
        print(f"  {feature}: {weight:.3f}")

    # Find representative users
    import numpy as np
    user_weights = np.array(result["user_weights"])
    basis_weights = user_weights[:, basis["basis_id"]]
    top_user_indices = np.argsort(basis_weights)[-3:][::-1]

    print(f"  Representative users:")
    for idx in top_user_indices:
        user = users[idx]
        weight = basis_weights[idx]
        print(f"    - {user.discord_handle} ({weight:.2f})")

    print()

# Export for manual review
import json
with open("./data/discovered_personas.json", "w") as f:
    json.dump(result, f, indent=2, default=str)

print(f"Full results exported to ./data/discovered_personas.json")
```

### Recipe 10: Performance Dashboard Data

**Goal**: Generate metrics for a real-time dashboard.

```python
# scripts/dashboard_metrics.py

from pathlib import Path
from datetime import datetime, timedelta
from insight_graph.core.graph import InsightGraph
from insight_graph.understand.sentiment import SentimentAnalyzer
import json

graph = InsightGraph(Path("./data/graph"))
analyzer = SentimentAnalyzer(graph)

# Time ranges
now = datetime.utcnow()
ranges = {
    "1h": now - timedelta(hours=1),
    "24h": now - timedelta(hours=24),
    "7d": now - timedelta(days=7),
}

metrics = {}

for label, since in ranges.items():
    messages = [m for m in graph.list_messages(limit=10000) if m.created_at >= since]
    issues = [i for i in graph.list_issues() if i.created_at >= since]

    trend = analyzer.get_sentiment_trend(messages)

    metrics[label] = {
        "messages": len(messages),
        "issues": len(issues),
        "sentiment": trend["avg_sentiment"],
        "frustration": trend["avg_frustration"],
        "trend": trend["trend"],
    }

# Overall stats
all_issues = graph.list_issues()
metrics["overall"] = {
    "total_users": len(graph.list_users()),
    "total_messages": len(graph.list_messages(limit=100000)),
    "total_issues": len(all_issues),
    "open_issues": len([i for i in all_issues if i.status.value in ["new", "triaged"]]),
    "personas": len(graph.list_personas()),
}

# Write to file (for dashboard to read)
with open("./data/dashboard_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print("Dashboard metrics updated")
```

**Update every 5 minutes**:
```cron
*/5 * * * * python /path/to/scripts/dashboard_metrics.py
```

## CI/CD Integration

### Recipe 11: Automated Testing in CI

**Goal**: Run tests and persona simulations in GitHub Actions.

```yaml
# .github/workflows/test.yml
name: Test & Analyze

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --cov=insight_graph

      - name: Generate demo data
        run: python scripts/init_demo_data.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - name: Run persona simulation
        run: |
          python -m insight_graph.personas.agents "Changes in PR: ${{ github.event.pull_request.title }}" > simulation.txt
          cat simulation.txt
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - name: Post simulation to PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const simulation = fs.readFileSync('simulation.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## Persona Impact Simulation\n\n' + simulation
            });
```

## Tips & Best Practices

### Performance Optimization

1. **Batch embeddings**: Generate embeddings in batches instead of one-by-one
2. **Cache RAG results**: Cache frequently queried contexts
3. **Index optimization**: Regularly rebuild vector store index
4. **Async operations**: Use async for I/O-bound operations

### Data Quality

1. **Regular deduplication**: Run weekly dedup passes
2. **Sentiment calibration**: Adjust sentiment thresholds based on community
3. **Persona refresh**: Re-run clustering monthly to capture shifts
4. **Clean old data**: Archive messages older than 6 months

### Security

1. **API authentication**: Add token-based auth to production API
2. **Rate limiting**: Implement rate limits on webhooks
3. **PII audits**: Regular audits of redaction effectiveness
4. **Access logs**: Monitor API access patterns

### Monitoring

1. **Alert thresholds**: Set up alerts for abnormal patterns
2. **Health checks**: Monitor all services with uptime checks
3. **Backup validation**: Regularly test restore process
4. **Capacity planning**: Track storage and API usage trends
