# Enrichment Status

Checks the current enrichment pipeline status on the dev server.

## Input

No arguments required.

## Steps

1. **Query enrichment counts** via the dev server API:
   ```bash
   curl -sf http://192.168.1.69:8000/api/enrich/status
   ```

2. **Query posting counts** for context:
   ```bash
   curl -sf http://192.168.1.69:8000/health
   ```

3. **Summarize** the results in a table:
   - Total postings vs enriched postings
   - Pass 1 complete vs Pass 2 complete
   - Latest enrichment run status and timestamp
   - Any errors or warnings

## If API is unreachable

Check if the server is running:
```bash
ssh compgraph-dev "systemctl status compgraph --no-pager"
```

Report the status and suggest `/deploy` if the service is down.
