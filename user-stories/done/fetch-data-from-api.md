# Fetch member data from API

## Background

To get us started, we imported the member data from
`/backend/data/seeds/member-data-export-2025-12-02T03-28-33.json`

## Goal

Create functionality to import current member data from the White Rabbit API.

## API Details

- **Endpoint:** `whiterabbitashland.com/docs/api` (needs verification)
- **API Key:** Stored in team password manager (do not commit to git)

---

## Implementation Plan

### Overview

Create functionality to fetch member data from the White Rabbit API and sync it with the local database. This extends the existing seed script rather than replacing it entirely.

### Immediate Next Step

> **Action Required:** Contact White Rabbit team to obtain API documentation.
> Specifically need: endpoint URL, authentication header format, and sample response.

---

### Prerequisites & Open Questions

**API Documentation Required:** The public endpoint at `whiterabbitashland.com/docs/api` doesn't expose API documentation. Before implementation, we need to:
1. Confirm the actual API endpoint URL (e.g., `/api/members`, `/api/v1/profiles`)
2. Confirm the authentication header format (e.g., `Authorization: Bearer <key>` or `X-API-Key: <key>`)
3. Confirm the response format matches our expected member data structure
4. Determine if there's pagination support for large datasets

**Assumption:** The API returns JSON data in a format similar to the existing seed file structure.

---

### Phased Approach

#### Phase 0: Manual Validation (Before Writing Code)

Validate the API works before building automation:

1. Use curl/httpx to hit the API endpoint manually
2. Verify authentication works with the secret key
3. Save response to a new JSON file in `data/seeds/`
4. Run existing `seed_members.py` with the new file to confirm data format

This de-risks the integration before investing in automation.

---

#### Phase 1: Core Implementation

##### Step 1: Extract Shared Utilities

**New File:** `backend/app/utils/data_normalization.py`

Extract helpers from `seed_members.py` for reuse:

```python
def normalize_string(value: str | None) -> str | None:
    """Convert empty strings to None for cleaner data."""

def normalize_list(value: list | None) -> list:
    """Ensure list is not None and filter empty strings."""

def parse_datetime(dt_string: str | None) -> datetime | None:
    """Parse datetime string from JSON export."""
```

Update `seed_members.py` to import from this module.

---

##### Step 2: Add Configuration

**File:** `backend/app/core/config.py`

```python
WHITE_RABBIT_API_URL: str = ""  # Set via environment variable
WHITE_RABBIT_API_KEY: str = ""  # Set via environment variable
```

**File:** `backend/.env.example`

```
WHITE_RABBIT_API_KEY=  # Obtain from team password manager
WHITE_RABBIT_API_URL=https://whiterabbitashland.com/api
```

---

##### Step 3: Create API Client

**New File:** `backend/app/services/white_rabbit_client.py`

```python
class WhiteRabbitClient:
    """Client for fetching member data from White Rabbit API."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    async def fetch_members(self) -> list[dict]:
        """Fetch all members from the White Rabbit API."""

    async def health_check(self) -> bool:
        """Verify API connectivity and authentication."""
```

Key implementation details:
- Use `httpx.AsyncClient` for async HTTP requests
- Retry logic with exponential backoff for transient failures
- Raise specific exceptions: `WhiteRabbitAuthError`, `WhiteRabbitAPIError`
- Log all API calls for debugging

---

##### Step 4: Extend Seed Script

**File:** `backend/app/scripts/seed_members.py`

Add `--from-api` flag to existing script:

```bash
# From file (existing behavior)
python -m app.scripts.seed_members --file data/seeds/export.json

# From API (new)
python -m app.scripts.seed_members --from-api

# From API with clear
python -m app.scripts.seed_members --from-api --clear

# Dry run (preview without committing)
python -m app.scripts.seed_members --from-api --dry-run
```

This keeps all member loading logic in one place.

---

##### Step 5: Add Tests

**New File:** `backend/tests/services/test_white_rabbit_client.py`

Test cases:
- Successful API fetch with mock response
- Authentication header sent correctly
- Error handling (401, 404, 500, timeout)
- Retry logic for transient failures

**File:** `backend/tests/scripts/test_seed_members.py`

Test cases:
- `--from-api` flag fetches from client
- Dry run doesn't commit changes
- Transaction rollback on partial failure

---

### Data Conflict Resolution Strategy

When syncing from API, local data may have been enriched by the profile optimizer agent.

**Strategy for v1: Only Fill Empty Fields**

- If local field is `NULL`/empty → use API value
- If local field has data → preserve local value
- Track `last_synced_from_api_at` timestamp on Member model

This is the safest approach that won't overwrite agent-generated improvements.

**Future consideration:** Per-field `source` tracking for more granular control.

---

### Transaction & Rollback Handling

All sync operations must be atomic:

```python
async with session.begin():
    # Process all members
    for member_data in api_response:
        await upsert_member(session, member_data)
    # Only commits if ALL succeed
# On any exception, entire transaction rolls back
```

This prevents partial sync states where some members are updated and others aren't.

---

### File Summary

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/utils/data_normalization.py` | Create | Shared helper functions |
| `backend/app/core/config.py` | Modify | Add API URL and key settings |
| `backend/.env.example` | Modify | Document new env vars |
| `backend/app/services/white_rabbit_client.py` | Create | HTTP client for WR API |
| `backend/app/scripts/seed_members.py` | Modify | Add `--from-api` flag |
| `backend/tests/services/test_white_rabbit_client.py` | Create | Client unit tests |

---

### Security Considerations

1. **API Key Storage:** Environment variables only, never commit to git
2. **Key in this file:** The API key was previously in this document - it has been removed and should be rotated
3. **Audit Logging:** Log all sync operations with timestamps
4. **Rate Limiting:** Respect any rate limits from the White Rabbit API

---

### Future Enhancements (Phase 2+)

1. **Admin Endpoint:** Add `/admin/sync-members` endpoint (requires admin role check via Clerk)
2. **Scheduled Sync:** Periodic sync via background task
3. **Webhook Support:** Listen for member update webhooks from White Rabbit
4. **Differential Sync:** Only fetch members updated since last sync
5. **Two-way Sync:** Push profile enrichments back to White Rabbit API
