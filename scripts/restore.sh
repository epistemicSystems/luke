#!/bin/bash
# Restore script for Insight Graph data

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo ""
    echo "Available backups:"
    ls -1 backups/graph_*.tar.gz 2>/dev/null | sed 's/.*graph_/  /' | sed 's/.tar.gz//' || echo "  No backups found"
    exit 1
fi

TIMESTAMP=$1
BACKUP_DIR="${BACKUP_DIR:-./backups}"
GRAPH_DATA_DIR="${GRAPH_DATA_DIR:-./data/graph}"
CHROMA_DATA_DIR="${CHROMA_PERSIST_DIR:-./data/chroma}"

echo "=== Insight Graph Restore ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Check if backups exist
if [ ! -f "$BACKUP_DIR/graph_$TIMESTAMP.tar.gz" ]; then
    echo "Error: Backup not found: $BACKUP_DIR/graph_$TIMESTAMP.tar.gz"
    exit 1
fi

# Confirm restore
read -p "This will replace current data. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Restore graph data
echo "Restoring graph data..."
rm -rf "$GRAPH_DATA_DIR"
mkdir -p "$GRAPH_DATA_DIR"
tar -xzf "$BACKUP_DIR/graph_$TIMESTAMP.tar.gz" -C "$GRAPH_DATA_DIR"
echo "✓ Graph data restored"

# Restore vector store
if [ -f "$BACKUP_DIR/chroma_$TIMESTAMP.tar.gz" ]; then
    echo "Restoring vector store..."
    rm -rf "$CHROMA_DATA_DIR"
    mkdir -p "$CHROMA_DATA_DIR"
    tar -xzf "$BACKUP_DIR/chroma_$TIMESTAMP.tar.gz" -C "$CHROMA_DATA_DIR"
    echo "✓ Vector store restored"
fi

echo ""
echo "=== Restore Complete ==="
