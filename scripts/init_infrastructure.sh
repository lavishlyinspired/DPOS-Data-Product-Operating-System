#!/bin/bash

echo "🐳 Starting DPOS Infrastructure..."

# Check if Docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: docker is not installed.' >&2
  exit 1
fi

# Start Services
docker-compose up -d neo4j kafka zookeeper ollama

echo "⏳ Waiting for Neo4j to start..."
sleep 15

echo "⏳ Waiting for Ollama to start..."
sleep 10

# Pull Ollama Model (Optional, if not present)
echo "🦙 Pulling Llama2 model (if needed)..."
docker exec dpos-ollama ollama pull llama2 2>/dev/null || echo "Model might already exist"

echo "✅ Infrastructure started."