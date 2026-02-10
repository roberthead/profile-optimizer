# Post Questions to White Rabbit HQ

AS a user
ON /questions
WHEN I click a [Share with HQ] button
I WANT to post to whiterabbitashland.com/profile/questions

## Notes

See https://whiterabbitashland.com/docs/api for the endpoints

Payload:
{
  "questionText": "What's your creative origin story?",
  "description": "Share how you got started",
  "questionType": "free_form",
  "source": "profile_optimizer",
  "category": "origin_story",
  "displayOrder": 1
  "notes": "This is a freeform field for things like specific people that should receive this question. And whatnot."
}

## Implementation Plan

### Context

Questions are generated and refined locally but there's no way to push them to the White Rabbit website. This feature adds a "Share with HQ" button per question so users can selectively post individual questions to `whiterabbitashland.com/profile/questions`. A confirmation modal lets the user review the payload and optionally add notes before sending.

### Step 1 — Add `post_question` to `WhiteRabbitClient`

**File:** `backend/app/services/white_rabbit_client.py`

Add a new method that POSTs to `/profile/questions` using the existing `_request` helper (which already handles auth headers, retries, and error handling):

```python
async def post_question(self, question_data: dict[str, Any]) -> dict[str, Any]:
    return await self._request("POST", "/profile/questions", json=question_data)
```

### Step 2 — Add `POST /api/v1/questions/share` backend endpoint

**File:** `backend/app/api/endpoints.py`

New request/response models and endpoint:
- `ShareQuestionRequest`: `question_id: int`, `notes: Optional[str]`
- `ShareQuestionResponse`: `success: bool`, `message: str`
- Endpoint loads the `Question` from DB, maps fields to the camelCase payload (questionText, description from purpose, questionType, source="profile_optimizer", category, displayOrder from order_index, notes), calls `WhiteRabbitClient.post_question()`, returns result.
- Returns 404 if question not found, 502 if the White Rabbit API call fails.

### Step 3 — Add "Share with HQ" button and confirmation modal to frontend

**File:** `frontend/src/pages/Questions.tsx`

- Add a `Share` (or `ExternalLink`) icon button to `QuestionCard` next to the existing badges, visible when the card is expanded.
- Clicking opens a confirmation modal (following the existing refine modal pattern) that shows the question text and has an optional "Notes" textarea.
- On confirm, fires a `useMutation` that POSTs to `/api/v1/questions/share` with the question ID and optional notes.
- Shows success/error feedback inline (green/red banner, following the existing `syncResult` pattern from MembersList).
- Button shows a spinner while the request is in flight.

### Step 4 — Verify end-to-end

1. Start backend (`uvicorn`) and frontend (`npm run dev`)
2. Navigate to `/questions`, expand a deck, expand a question
3. Click "Share with HQ", optionally add notes, confirm
4. Verify the POST reaches the White Rabbit API (check backend logs for the `_request` debug log)
5. Verify success/error feedback displays correctly in the UI

### Files to modify

| File | Change |
|------|--------|
| `backend/app/services/white_rabbit_client.py` | Add `post_question()` method |
| `backend/app/api/endpoints.py` | Add `ShareQuestionRequest`, `ShareQuestionResponse`, `POST /questions/share` endpoint |
| `frontend/src/pages/Questions.tsx` | Add Share button to `QuestionCard`, confirmation modal, mutation |
