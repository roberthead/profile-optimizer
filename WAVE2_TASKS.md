# Wave 2 Implementation Tasks

## Status: COMPLETED ✓

All Wave 2 tasks have been implemented.

## Overview
Following Wave 1 completion, these tasks address identified gaps and add the dedicated GroupQuestionAgent.

---

## Task 1: GroupQuestionAgent (Priority: HIGH) ✓ COMPLETED

**Description:** Create a dedicated LLM-powered agent specifically for group context question selection. This agent understands group dynamics and generates questions that spark conversation among the people present.

**Why:** Current `/display/group-question` endpoint uses heuristic logic. An LLM agent can:
- Analyze relationships between present members (their edges, patterns)
- Generate questions that bridge different member interests
- Consider past conversations and what topics haven't been explored
- Craft questions with appropriate vibe for the group energy

**File:** `backend/app/agents/group_question.py`

**Agent Capabilities:**
- Analyze present member profiles and their connections
- Consider time/meeting context
- Generate contextual questions that connect multiple people
- Suggest icebreakers based on shared patterns/edges
- Avoid questions that might exclude some members

**Tools needed:**
- `GET_PRESENT_MEMBERS_TOOL` - Get profiles of members present
- `GET_GROUP_EDGES_TOOL` - Get edges between present members
- `GET_RECENT_GROUP_QUESTIONS_TOOL` - Avoid repetition
- `SCORE_QUESTION_FOR_GROUP_TOOL` - Evaluate question fit

---

## Task 2: Group Question Tools ✓ COMPLETED

**Description:** Create tools for the GroupQuestionAgent.

**File:** `backend/app/tools/group_tools.py`

**Tools:**
```python
GET_PRESENT_MEMBERS_TOOL = {
    "name": "get_present_members",
    "description": "Get full profiles of members currently present"
}

GET_GROUP_EDGES_TOOL = {
    "name": "get_group_edges",
    "description": "Get all edges between the present members"
}

GET_RECENT_GROUP_QUESTIONS_TOOL = {
    "name": "get_recent_group_questions",
    "description": "Get questions asked to this group recently to avoid repetition"
}
```

---

## Task 3: Integrate GroupQuestionAgent into Endpoint ✓ COMPLETED

**Description:** Update `/display/group-question` endpoint to use the new agent.

**File:** `backend/app/api/display_endpoints.py`

**Changes:**
- Import GroupQuestionAgent
- Replace heuristic logic with agent call
- Keep fallback to heuristics if agent fails
- Add agent response caching to avoid redundant LLM calls

---

## Task 4: Group Question Session Tracking

**Description:** Track which questions were asked to which group so the agent can avoid repetition.

**Model addition to `models.py`:**
```python
class GroupQuestionSession(Base):
    __tablename__ = "group_question_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_date: Mapped[datetime]
    time_of_day: Mapped[str]
    meeting_name: Mapped[Optional[str]]
    present_member_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    targeting_reason: Mapped[str]
    created_at: Mapped[datetime]
```

**Migration:** Add alembic migration for new table.

---

## Task 5: Demo Page Enhancement ✓ COMPLETED

**Description:** Improve Demo.tsx to show group context controls.

**Enhancements:**
- Add time-of-day selector
- Add meeting dropdown (AI Cohort, Creator Workshop, etc.)
- Add member presence checkboxes
- Show targeting reason more prominently
- Add "refresh group question" button with different contexts

---

## Task 6: Pre-deployment Setup Tasks

**Description:** Essential setup before running the system.

**Checklist:**
- [ ] Run alembic migration: `alembic upgrade head`
- [ ] Install frontend deps: `cd frontend && npm install react-force-graph-2d`
- [ ] Add ROVA_API_KEY to `.env` (if Rova integration needed)
- [ ] Seed initial patterns if needed
- [ ] Generate initial question deck

---

## Execution Order

1. **Task 4** - Group session tracking model + migration (foundation)
2. **Task 2** - Group tools (agent dependency)
3. **Task 1** - GroupQuestionAgent (core feature)
4. **Task 3** - Integrate agent into endpoint
5. **Task 5** - Demo page enhancement
6. **Task 6** - Pre-deployment setup

---

## Agent Distribution After Wave 2

| Agent | Responsibility |
|-------|---------------|
| EdgeDiscoveryAgent | Discovers member-to-member connections |
| TasteProfileAgent | Builds evolving preference profiles |
| QuestionTargetingAgent | Targets questions to individual members |
| **GroupQuestionAgent** | Selects questions for group contexts |
| PatternFinderAgent | Identifies community patterns |
| QuestionDeckAgent | Generates question banks |
| ProfileChatAgent | Conversational profile building |
| ProfileEvaluationAgent | Evaluates profile completeness |

This separation keeps each agent focused and avoids overloading any single agent with too many responsibilities.
