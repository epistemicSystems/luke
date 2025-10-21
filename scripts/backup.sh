#!/bin/bash
# Backup script for Insight Graph data

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
GRAPH_DATA_DIR="${GRAPH_DATA_DIR:-./data/graph}"
CHROMA_DATA_DIR="${CHROMA_PERSIST_DIR:-./data/chroma}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "=== Insight Graph Backup ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup graph data
echo "Backing up graph data..."
tar -czf "$BACKUP_DIR/graph_$TIMESTAMP.tar.gz" -C "$GRAPH_DATA_DIR" .
echo "✓ Graph data backed up to $BACKUP_DIR/graph_$TIMESTAMP.tar.gz"

# Backup vector store
if [ -d "$CHROMA_DATA_DIR" ]; then
    echo "Backing up vector store..."
    tar -czf "$BACKUP_DIR/chroma_$TIMESTAMP.tar.gz" -C "$CHROMA_DATA_DIR" .
    echo "✓ Vector store backed up to $BACKUP_DIR/chroma_$TIMESTAMP.tar.gz"
fi

# Keep only last 7 backups
echo ""
echo "Cleaning up old backups (keeping last 7)..."
ls -t "$BACKUP_DIR"/graph_*.tar.gz | tail -n +8 | xargs -r rm
ls -t "$BACKUP_DIR"/chroma_*.tar.gz | tail -n +8 | xargs -r rm

echo ""
echo "=== Backup Complete ==="
