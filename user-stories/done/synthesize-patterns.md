# Synthesize patterns

We need to build a patterns table and an agent to populate it.

Pattern
name
description
(timestamps)

The PatternFinder agent should identify interesting pattern in the member datasets.

The goal is to identify conceptual relationships that existing among the membership. This information will be source data for generating interesting questions that build on that info to ask in the future.

## Implementation Plan

### Step 1: Create Pattern Model and Migration

**File: `backend/app/models.py`**

Add a new `Pattern` model:

```python
class PatternCategory(str, PyEnum):
    """Categories for discovered patterns."""
    SKILL_CLUSTER = "skill_cluster"           # Groups of related skills that appear together
    INTEREST_THEME = "interest_theme"         # Common interest areas/passions
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"  # Complementary skills/potential partnerships
    COMMUNITY_STRENGTH = "community_strength" # Core competencies of the community
    CROSS_DOMAIN = "cross_domain"             # Interesting overlaps between different areas

class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), unique=True)  # Unique to prevent duplicates
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[PatternCategory] = mapped_column(Enum(PatternCategory), index=True)

    # Evidence and context
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    related_member_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), default=list)  # Members exhibiting this pattern
    evidence: Mapped[Optional[dict]] = mapped_column(JSON)  # Supporting data (skill names, frequencies, etc.)

    # For question generation
    question_prompts: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
```

**Changes from original:**
- Removed `pattern_id` UUID (unnecessary, just use `id`)
- Removed `confidence_score` (unclear how to calculate for v1)
- Added `unique=True` on `name` to prevent duplicates
- Added `index=True` on `category` for filtering
- Reduced categories from 7 to 5 essential ones
- Added `related_member_ids` array to track which members exhibit the pattern

**Create migration:**
```bash
cd backend
alembic revision --autogenerate -m "Add patterns table"
alembic upgrade head
```

### Step 2: Add Pattern Tools to Existing File

**File: `backend/app/tools/question_tools.py`** (extend existing file)

Reuse `get_community_profile_analysis` which already provides rich member data with skill/interest frequencies. Just add `save_pattern`:

```python
from app.models import Pattern, PatternCategory

async def save_pattern(db: AsyncSession, pattern_data: dict) -> dict:
    """Save or update a discovered pattern."""
    # Check for existing pattern by name (upsert behavior)
    existing = await db.execute(
        select(Pattern).where(Pattern.name == pattern_data["name"])
    )
    pattern = existing.scalar_one_or_none()

    if pattern:
        # Update existing
        for key, value in pattern_data.items():
            setattr(pattern, key, value)
    else:
        # Create new
        pattern = Pattern(**pattern_data)
        db.add(pattern)

    await db.commit()
    await db.refresh(pattern)
    return {"id": pattern.id, "name": pattern.name, "created": pattern is None}

SAVE_PATTERN_TOOL = {
    "name": "save_pattern",
    "description": "Save a discovered pattern. If a pattern with the same name exists, it will be updated.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short, unique pattern name"},
            "description": {"type": "string", "description": "Detailed description of what this pattern reveals"},
            "category": {"type": "string", "enum": ["skill_cluster", "interest_theme", "collaboration_opportunity", "community_strength", "cross_domain"]},
            "member_count": {"type": "integer", "description": "Number of members exhibiting this pattern"},
            "related_member_ids": {"type": "array", "items": {"type": "integer"}, "description": "IDs of members who exhibit this pattern"},
            "evidence": {"type": "object", "description": "Supporting data (skill names, frequencies, etc.)"},
            "question_prompts": {"type": "array", "items": {"type": "string"}, "description": "2-3 questions that could explore this pattern further"}
        },
        "required": ["name", "description", "category", "member_count"]
    }
}
```

### Step 3: Create PatternFinderAgent

**File: `backend/app/agents/pattern_finder.py`**

```python
SYSTEM_PROMPT = """You are a community analyst for White Rabbit Ashland, a creative community.
Your task is to discover meaningful patterns in member data that reveal:

1. **Skill Clusters** - Groups of related skills that appear together (e.g., "Design + Frontend + UX")
2. **Interest Themes** - Common passions or curiosities shared by multiple members
3. **Collaboration Opportunities** - Complementary skills that could lead to partnerships
4. **Community Strengths** - Core competencies where the community has deep expertise
5. **Cross-Domain Connections** - Unexpected overlaps between different areas

For each pattern you discover:
- Give it a clear, memorable name
- Explain what it reveals about the community
- List which members exhibit this pattern
- Suggest 2-3 questions that could explore this pattern further

Focus on patterns that are:
- Actionable (could lead to introductions, events, or collaborations)
- Non-obvious (reveal something beyond simple skill/interest counts)
- Community-building (strengthen connections between members)

Aim to discover 5-10 high-quality patterns per analysis."""

class PatternFinderAgent:
    """Agent that discovers patterns in member data."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def discover_patterns(self) -> dict:
        """Analyze member data and discover patterns."""
        # 1. Call get_community_profile_analysis tool
        # 2. Claude analyzes data and calls save_pattern for each pattern found
        # 3. Return summary of patterns discovered

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool and return result."""
        if tool_name == "get_community_profile_analysis":
            return await get_community_profile_analysis(self.db)
        elif tool_name == "save_pattern":
            return await save_pattern(self.db, tool_input)
        return {"error": f"Unknown tool: {tool_name}"}
```

### Step 4: Add API Endpoints

**File: `backend/app/api/endpoints.py`**

```python
@router.post("/patterns/discover")
async def discover_patterns(
    focus_areas: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
):
    """Run pattern discovery on member data."""
    agent = PatternFinderAgent(db)
    result = await agent.discover_patterns(focus_areas)
    return result

@router.get("/patterns")
async def list_patterns(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List discovered patterns."""

@router.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific pattern."""
```

### Step 5: Add Tests

**File: `backend/tests/agents/test_pattern_finder.py`**

- Test pattern tool data aggregation
- Test pattern saving
- Test agent initialization
- Mock Claude responses for pattern discovery

### Step 6: Frontend (Optional/Future)

Add a "Patterns" page to view discovered patterns:
- List patterns by category
- Show member count and confidence
- Display suggested questions
- Button to trigger pattern refresh

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `backend/app/models.py` | Add Pattern model, PatternCategory enum |
| `backend/alembic/versions/xxx_add_patterns.py` | Migration (auto-generated) |
| `backend/app/tools/question_tools.py` | Add save_pattern function and SAVE_PATTERN_TOOL |
| `backend/app/agents/pattern_finder.py` | Create new file |
| `backend/app/agents/__init__.py` | Export PatternFinderAgent |
| `backend/app/api/endpoints.py` | Add pattern endpoints |
| `backend/tests/agents/test_pattern_finder.py` | Create new file |

---

## Verification

1. Run migration: `alembic upgrade head`
2. Run tests: `pytest tests/agents/test_pattern_finder.py -v`
3. Test API manually:
   ```bash
   # Discover patterns
   curl -X POST http://localhost:8000/api/v1/patterns/discover

   # List patterns
   curl http://localhost:8000/api/v1/patterns
   ```
4. Verify patterns are saved to database with reasonable categories and descriptions
