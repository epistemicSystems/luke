# Deployment Guide

Production deployment options for Insight Graph.

## Deployment Options

### 1. Docker Compose (Recommended)

The easiest way to deploy Insight Graph in production.

```bash
# Set environment variables
cp .env.example .env
# Edit .env with production credentials

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- **API**: REST API on port 8000
- **Discord Bot**: Background ingestion service

### 2. Manual Deployment

For custom setups or cloud platforms.

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
python -m uvicorn insight_graph.api.server:app --host 0.0.0.0 --port 8000

# In another terminal, start Discord bot
python -m insight_graph.ingest.discord_bot
```

### 3. Cloud Platforms

#### Heroku

```bash
# Create Procfile
web: uvicorn insight_graph.api.server:app --host 0.0.0.0 --port $PORT
worker: python -m insight_graph.ingest.discord_bot

# Deploy
git push heroku main
heroku scale web=1 worker=1
```

#### AWS (ECS/Fargate)

Use the provided `Dockerfile` to build and deploy to ECS.

#### Google Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/insight-graph

# Deploy
gcloud run deploy insight-graph \
  --image gcr.io/PROJECT_ID/insight-graph \
  --platform managed \
  --set-env-vars OPENAI_API_KEY=xxx,DISCORD_TOKEN=yyy
```

## Environment Variables

Required for production:

```bash
# Discord
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id

# OpenAI
OPENAI_API_KEY=your_api_key

# Storage paths
GRAPH_DATA_DIR=/app/data/graph
CHROMA_PERSIST_DIR=/app/data/chroma

# API
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

## Monitoring

### Health Checks

The API exposes health check endpoints:

```bash
# Check API health
curl http://localhost:8000/health

# Get stats
curl http://localhost:8000/stats
```

### Automated Monitoring

Use the provided health check script:

```bash
./scripts/health_check.sh
```

Set up a cron job:

```cron
*/5 * * * * /path/to/scripts/health_check.sh >> /var/log/insight-graph-health.log 2>&1
```

### Metrics to Track

- API response times
- Graph entity counts (users, messages, issues)
- Vector store size
- Discord bot uptime
- Error rates in logs

## Backup & Restore

### Automated Backups

Set up daily backups with cron:

```cron
0 2 * * * /path/to/scripts/backup.sh >> /var/log/insight-graph-backup.log 2>&1
```

### Manual Backup

```bash
./scripts/backup.sh
```

Backups are stored in `./backups/` with timestamps.

### Restore

```bash
# List available backups
./scripts/restore.sh

# Restore from specific timestamp
./scripts/restore.sh 20240115_020000
```

## Scaling

### Horizontal Scaling

The API server is stateless and can be scaled horizontally:

```bash
# Docker Compose
docker-compose up -d --scale api=3

# Kubernetes
kubectl scale deployment insight-graph-api --replicas=3
```

### Database Optimization

For large deployments (>1M messages):

1. Consider PostgreSQL for graph storage instead of JSON files
2. Use a managed ChromaDB instance
3. Implement caching (Redis) for frequent queries

### Performance Tuning

- **Embeddings**: Batch embed messages during ingestion
- **RAG**: Implement query result caching
- **Briefs**: Pre-generate and cache daily briefs
- **Personas**: Cache simulation results

## Security

### Production Checklist

- [ ] Change default credentials
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Restrict CORS origins in `api/server.py`
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Enable rate limiting on API endpoints
- [ ] Set up firewall rules
- [ ] Regular security updates

### Securing Discord Bot

- Bot token should be kept secret
- Use Discord's permission system to restrict channels
- Enable 2FA on Discord account managing the bot

### API Security

Add authentication to the API:

```python
# In api/server.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/chat")
def chat(request: ChatRequest, credentials = Security(security)):
    # Verify token
    if credentials.credentials != os.getenv("API_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid token")
    # ... rest of endpoint
```

## Troubleshooting

### Bot Not Receiving Messages

1. Check bot permissions in Discord
2. Verify `DISCORD_TOKEN` is correct
3. Ensure bot is in the server
4. Check bot logs for errors

### API Errors

1. Check `OPENAI_API_KEY` is valid
2. Verify data directories exist and are writable
3. Check logs: `docker-compose logs api`

### Vector Store Issues

1. Delete and reinitialize: `rm -rf data/chroma`
2. Re-run ingestion to rebuild embeddings

### Out of Disk Space

1. Run cleanup: `docker system prune -a`
2. Archive old backups
3. Implement log rotation

## Maintenance

### Regular Tasks

**Daily**:
- Monitor health checks
- Review error logs
- Check disk usage

**Weekly**:
- Verify backups are successful
- Review performance metrics
- Update dependencies (if needed)

**Monthly**:
- Security updates
- Capacity planning review
- User feedback analysis

### Updating

```bash
# Docker Compose
git pull origin main
docker-compose build
docker-compose up -d

# Manual
git pull origin main
pip install -r requirements.txt
# Restart services
```

## Support

For production support:
- Check logs first: `docker-compose logs`
- Review [API docs](./API.md)
- File issues on GitHub
