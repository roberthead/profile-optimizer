# Profile Optimizer v2: Non-Deterministic Graph System

## Implementation Plan - February 2026

### Vision
Transform Profile Optimizer from a form-filling tool into a living, breathing community graph that discovers connections, generates contextual questions, and delivers personalized experiences across multiple touchpoints.

**Core Principles:**
- Non-deterministic: Questions emerge from the graph, not templates
- Graph-first: Members are nodes, patterns are clusters, edges connect people
- Multi-channel: Mobile swipe, clubhouse display, email, SMS
- Taste-aware: Evolving profiles that learn from behavior, not just explicit input

---

## Wave 1: Data Foundation
*Goal: Extend the data model to support graph relationships and taste profiles*

### 1.1 New Database Models

#### MemberEdge (member-to-member connections)
```python
class MemberEdge(Base):
    __tablename__ = "member_edges"

    id: int (PK)
    member_a_id: int (FK -> members)
    member_b_id: int (FK -> members)
    edge_type: Enum [
        "shared_skill",
        "shared_interest",
        "collaboration_potential",
        "event_co_attendance",
        "introduced_by_agent",
        "pattern_connection"
    ]
    strength: Float (0.0 - 1.0)
    discovered_via: String  # "pattern_finder", "question_response", "event_signal", "manual"
    evidence: JSON  # {pattern_id, question_id, event_id, notes}
    is_active: Boolean
    created_at, updated_at: DateTime
```

#### TasteProfile (evolving member preferences)
```python
class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    id: int (PK)
    member_id: int (FK -> members, unique)

    # Explicit (from interviews)
    vibe_words: ARRAY(String)  # ["cozy", "weird", "intimate"]
    avoid_words: ARRAY(String)  # ["crowded", "loud", "corporate"]
    energy_time: String  # "morning", "afternoon", "evening", "night"
    usual_company: String  # "solo", "duo", "group", "varies"
    spontaneity: Float  # 0.0 (planner) to 1.0 (spontaneous)

    # Anti-preferences (dealbreakers)
    dealbreakers: ARRAY(String)  # ["standing room", "no parking", "cash only"]
    not_my_thing: ARRAY(String)  # Things they just don't get

    # Implicit (learned from behavior) - JSON for flexibility
    category_affinities: JSON  # {"Live Music": 0.8, "Workshops": 0.3}
    venue_affinities: JSON  # {"Varsity Theatre": 0.9, "Brickroom": 0.7}
    organizer_affinities: JSON  # {"Ashland Folk Collective": 0.8}
    price_comfort: JSON  # {"min": 0, "max": 50, "sweet_spot": 15}

    # Contextual (temporary state)
    current_mood: String
    this_week_energy: String  # "low", "medium", "high"
    visitors_in_town: Boolean
    context_updated_at: DateTime

    created_at, updated_at: DateTime
```

#### EventSignal (Rova event interactions)
```python
class EventSignal(Base):
    __tablename__ = "event_signals"

    id: int (PK)
    member_id: int (FK -> members)
    rova_event_id: String  # "event.xxx"
    rova_event_slug: String
    signal_type: Enum [
        "viewed",
        "clicked",
        "rsvp",
        "attended",
        "skipped",  # saw but didn't engage
        "shared",
        "organized"
    ]

    # Denormalized event context for analysis
    event_category: String
    event_venue_slug: String
    event_organizer_slug: String
    event_tags: ARRAY(String)
    event_time_of_day: String  # "morning", "afternoon", "evening", "night"
    event_day_of_week: String

    signal_strength: Float  # 1.0 for attended, 0.5 for RSVP, -0.3 for skipped
    created_at: DateTime
```

#### QuestionDelivery (multi-channel question tracking)
```python
class QuestionDelivery(Base):
    __tablename__ = "question_deliveries"

    id: int (PK)
    question_id: int (FK -> questions)
    member_id: int (FK -> members)

    channel: Enum ["mobile_swipe", "clubhouse_display", "email", "sms", "web_chat"]
    delivery_status: Enum ["pending", "delivered", "viewed", "answered", "skipped", "expired"]

    delivered_at: DateTime
    viewed_at: DateTime
    answered_at: DateTime

    response_type: String  # "yes", "no", "skip", "text", "choice"
    response_value: Text
    response_time_seconds: Integer  # How long they took

    context: JSON  # Why this question was selected for this member

    created_at: DateTime
```

### 1.2 Extend Existing Models

#### Question (add targeting context)
```python
# Add to Question model:
relevant_member_ids: ARRAY(Integer)  # Members this question is about
notes: Text  # Why we're asking this (context for AI and display)
edge_context: JSON  # {edge_id, edge_type, connected_member_name}
targeting_criteria: JSON  # {pattern_ids, skill_match, interest_match, randomness_weight}
vibe: String  # "warm", "playful", "deep", "edgy"
```

#### Pattern (add graph metadata)
```python
# Add to Pattern model:
edge_count: Integer  # How many edges this pattern has created
question_count: Integer  # How many questions generated from this
last_question_generated_at: DateTime
vitality_score: Float  # How "alive" this pattern is (recent activity)
```

### 1.3 Alembic Migrations
- `add_member_edges_table.py`
- `add_taste_profiles_table.py`
- `add_event_signals_table.py`
- `add_question_deliveries_table.py`
- `extend_questions_with_context.py`
- `extend_patterns_with_graph_metadata.py`

---

## Wave 2: Graph Agents
*Goal: Build agents that discover edges, target questions, and evolve taste profiles*

### 2.1 EdgeDiscoveryAgent
**Purpose:** Find connections between members based on shared attributes, patterns, and behaviors

**Tools:**
- `get_all_members_with_profiles` - Fetch member data for analysis
- `get_existing_edges` - Avoid duplicate edge creation
- `get_active_patterns` - Use patterns as edge evidence
- `save_edge` - Create new member-to-member edges

**Behavior:**
1. Analyze member pairs for shared skills/interests
2. Calculate edge strength based on overlap depth
3. Look for non-obvious connections (cross-domain overlaps)
4. Create edges with evidence trail

**Output Example:**
```json
{
  "edges_discovered": 12,
  "edge_types": {
    "shared_skill": 5,
    "shared_interest": 4,
    "collaboration_potential": 3
  },
  "strongest_edge": {
    "members": ["Alice", "Bob"],
    "type": "collaboration_potential",
    "strength": 0.85,
    "evidence": "Alice (UX design) + Bob (React dev) = potential product team"
  }
}
```

### 2.2 QuestionTargetingAgent
**Purpose:** Determine which member(s) should receive which question

**Tools:**
- `get_question_pool` - Available questions to assign
- `get_member_context` - Member's profile, taste, recent activity
- `get_member_edges` - Who they're connected to
- `get_answered_questions` - What they've already answered
- `assign_question_to_member` - Create delivery record

**Behavior:**
1. Score each question-member pair based on:
   - Pattern relevance
   - Edge context (question involves someone they're connected to)
   - Taste profile match (vibe alignment)
   - Freshness (haven't been asked similar recently)
   - Randomness factor (serendipity injection)
2. Weight by channel (some questions better for mobile vs email)
3. Create delivery records with context

**Non-Deterministic Elements:**
- 70% relevance-based selection
- 20% pattern/edge-based selection
- 10% random wildcard (serendipity)

### 2.3 TasteProfileAgent
**Purpose:** Build and evolve taste profiles from conversations and behavior

**Tools:**
- `get_conversation_history` - Past chat with member
- `get_question_responses` - Their answers to questions
- `get_event_signals` - Rova interactions
- `get_current_taste_profile` - Existing profile
- `update_taste_profile` - Save evolved profile

**Behavior:**
1. Analyze conversation for vibe words, preferences, dealbreakers
2. Extract implicit preferences from behavior patterns
3. Detect contextual state changes ("I'm tired this week")
4. Update profile with decay (old signals fade)

**Conversation Triggers:**
- "That sounds exhausting" → avoid_words: ["high-energy"]
- "I love weird stuff" → vibe_words: ["weird", "experimental"]
- "I never go downtown" → venue_affinities: {"downtown": -0.5}

### 2.4 QuestionGeneratorAgent (Enhanced)
**Purpose:** Generate questions that emerge from the graph, not templates

**Tools:**
- `get_active_patterns` - Pattern context
- `get_member_edges` - Relationship context
- `get_community_gaps` - What's missing across profiles
- `get_recent_responses` - What's working
- `save_contextual_question` - Save with full context

**Question Types by Vibe:**
```
warm: "What's a skill you wish you could borrow from someone in this community?"
playful: "If you could swap lives with another member for a day, who and why?"
deep: "What's a project you abandoned that still calls to you?"
edgy: "What's something this community does that you secretly think is overrated?"
connector: "You and [Name] both love [interest]. Have you ever talked about it?"
```

---

## Wave 3: Rova Integration
*Goal: Connect to Rova events for behavioral signals and event-based recommendations*

### 3.1 RovaClient Service
```python
class RovaClient:
    """Async client for Rova public API"""

    async def fetch_events(self, **filters) -> list[Event]
    async def fetch_venues(self) -> list[Venue]
    async def fetch_organizers(self) -> list[Organizer]
    async def fetch_categories(self) -> list[Category]
    async def fetch_event_by_slug(self, slug: str) -> Event
```

### 3.2 Event Sync Job
- Periodic sync of upcoming events (daily)
- Store event metadata locally for fast access
- Track which members are associated with which organizers

### 3.3 Event Signal Endpoints
```
POST /api/v1/events/signal
{
  "member_id": 1,
  "rova_event_id": "event.xxx",
  "signal_type": "rsvp"
}
```

### 3.4 EventRecommendationAgent
**Purpose:** Recommend events based on taste profile + community context

**Tools:**
- `get_member_taste_profile`
- `get_upcoming_events`
- `get_member_edges` - "Your friend Alice is going"
- `score_event_for_member`

**Output:**
```json
{
  "event": "Jazz Night at Brickroom",
  "score": 0.87,
  "reasons": [
    "Matches your 'live music' affinity (0.9)",
    "Evening timing fits your energy pattern",
    "2 members you're connected to are going"
  ]
}
```

---

## Wave 4: Multi-Channel Delivery
*Goal: Deliver questions and content across mobile, display, email, SMS*

### 4.1 Mobile Swipe Interface (React Native / PWA)

**Screen: Question Card**
```
┌─────────────────────────────────────┐
│  QUESTION OF THE MOMENT             │
│                                     │
│  "What's a skill you'd love to      │
│   borrow from someone here?"        │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Context: You're part of the │   │
│  │ "Creative Technologists"    │   │
│  │ pattern with 8 others       │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────┐  ┌─────┐  ┌─────────┐     │
│  │ 👎  │  │ ⏭️  │  │  💬     │     │
│  │Skip │  │Later│  │ Answer  │     │
│  └─────┘  └─────┘  └─────────┘     │
│                                     │
└─────────────────────────────────────┘
```

**Swipe Gestures:**
- Left: Skip (not interested)
- Right: Answer (opens text input or choices)
- Up: Save for later
- Down: "Not my vibe" (negative signal)

**API Endpoints:**
```
GET  /api/v1/mobile/questions/next?member_id=1
POST /api/v1/mobile/questions/{id}/respond
POST /api/v1/mobile/questions/{id}/skip
POST /api/v1/mobile/questions/{id}/save
```

### 4.2 Clubhouse Digital Display

**Question of the Day Board**
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   🐰 WHITE RABBIT QUESTION OF THE DAY                      │
│                                                             │
│   "What's a collaboration you'd love to see                │
│    happen between two people here?"                        │
│                                                             │
│   ─────────────────────────────────────────                │
│                                                             │
│   Recent answers:                                           │
│   • "Sarah + Mike on that AI art project" - Alex           │
│   • "Would love to see the musicians jam with..." - Jo     │
│                                                             │
│   Scan to answer: [QR CODE]                                 │
│                                                             │
│   Pattern of the Week: "Audio Creators" (12 members)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Display Modes:**
- Question of the Day (rotates daily)
- Pattern Spotlight (weekly feature)
- New Connections (recently discovered edges)
- Event Recommendations (from Rova)

**API Endpoints:**
```
GET /api/v1/display/question-of-the-day
GET /api/v1/display/pattern-spotlight
GET /api/v1/display/recent-connections
GET /api/v1/display/recommended-events
```

### 4.3 Email Templates

**Weekly Digest Email**
```
Subject: Your White Rabbit Week: 3 new connections discovered

Hey [Name],

This week in your community graph:

🔗 NEW CONNECTIONS
You and Marcus both love fermentation AND woodworking.
Small world, right? [See Marcus's profile]

❓ QUESTION FOR YOU
"What's something you're working on that you'd
love a second opinion on?"
[Answer now] [Skip]

🎭 EVENTS THAT FIT YOU
Based on your taste profile:
• Jazz Night at Brickroom (Sat 8pm) - 2 connections going
• Sourdough Workshop (Sun 10am) - matches your interests

📊 YOUR GRAPH
Profile completeness: 73% (+5% this week)
Connections: 8 members
Patterns: 3 clusters

[View your graph →]
```

**Event Recommendation Email**
```
Subject: [Name], this looks like your kind of thing

Hey [Name],

Quick heads up about an event that pinged your taste profile:

🎵 "Experimental Sound Night at Brickroom"
   Friday 8pm | $15 | 21+

Why we thought of you:
• You mentioned loving "weird" and "experimental" stuff
• Your friend Sarah is going
• Evening timing matches your energy pattern
• Brickroom is one of your favorite venues

[Check it out on Rova →]

Not your thing? [Tell us why] - it helps us learn
```

### 4.4 SMS Messages

**Question Nudge**
```
🐰 Quick one from White Rabbit:

"What's a conversation you've been
meaning to have with someone here?"

Reply to answer, or 'skip' to pass
```

**Event Alert**
```
🐰 Heads up: Jazz at Brickroom tonight 8pm

3 people you're connected to are going.
Fits your "spontaneous evening" vibe.

More info: rova.live/events/jazz-night
```

**Connection Nudge**
```
🐰 You and Alex have been in the same
pattern for 3 weeks but haven't met.

They're at the clubhouse right now.
Just saying. 👀
```

---

## Wave 5: Graph Visualization UI
*Goal: Build a demo page showing the community graph and data model*

### 5.1 Graph Visualization Page (`/graph`)

**Features:**
- Interactive node-link diagram (D3.js or vis.js)
- Members as nodes (sized by connection count)
- Edges as lines (thickness = strength, color = type)
- Patterns as cluster backgrounds
- Click node to see member details
- Click edge to see connection evidence
- Filter by pattern, edge type, time range

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  COMMUNITY GRAPH                                    [Patterns ▼] [Edges ▼]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│           ┌───┐                    ┌───┐                                   │
│          /│ A │\                  /│ E │                                   │
│         / └───┘ \                / └───┘                                   │
│        /    │    \              /                                          │
│    ┌───┐   │   ┌───┐      ┌───┐                                           │
│    │ B │───┼───│ C │──────│ F │     [Pattern: Creative Technologists]     │
│    └───┘   │   └───┘      └───┘                                           │
│        \   │   /                                                           │
│         \  │  /                                                            │
│          ┌───┐                                                             │
│          │ D │                                                             │
│          └───┘                                                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  SELECTED: Alice Chen                                                       │
│  Connections: 5 | Patterns: 2 | Profile: 78%                               │
│  Edges: Bob (shared_skill: 0.8), Carol (collaboration: 0.6)                │
│  Recent: Answered 2 questions, RSVP'd to Jazz Night                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Data Model Explorer Page (`/data-model`)

**Features:**
- Entity relationship diagram
- Live counts for each table
- Sample data display
- Recent activity feed

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DATA MODEL EXPLORER                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   MEMBERS   │────▶│   EDGES     │◀────│  PATTERNS   │                   │
│  │    (82)     │     │   (156)     │     │    (12)     │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│        │                   │                   │                            │
│        ▼                   ▼                   ▼                            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │TASTE PROFILE│     │  QUESTIONS  │     │ DELIVERIES  │                   │
│  │    (45)     │     │   (234)     │     │   (1,205)   │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│        │                                       │                            │
│        ▼                                       ▼                            │
│  ┌─────────────┐                         ┌─────────────┐                   │
│  │EVENT SIGNALS│                         │  RESPONSES  │                   │
│  │   (328)     │                         │   (892)     │                   │
│  └─────────────┘                         └─────────────┘                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECENT ACTIVITY                                                            │
│  • Edge discovered: Alice ↔ Bob (shared_skill, 0.85)          2 min ago    │
│  • Question answered: "What energizes you?" by Carol          5 min ago    │
│  • Pattern updated: "AI Enthusiasts" now has 14 members      12 min ago    │
│  • Taste profile evolved: Dave added "jazz" affinity         15 min ago    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Demo Dashboard Page (`/demo`)

**All-in-one demo view:**
- Graph visualization (small)
- Current question of the day
- Recent connections
- Sample mobile card preview
- Sample email preview
- Live stats

---

## Wave 6: Polish & Integration
*Goal: Wire everything together, add polish, prepare for demo*

### 6.1 API Completeness
- All endpoints documented with OpenAPI
- Error handling standardized
- Rate limiting added
- Authentication integrated

### 6.2 Agent Orchestration
- Scheduler for periodic agent runs
- Edge discovery: daily
- Taste profile updates: on new data
- Question targeting: hourly
- Event sync: every 6 hours

### 6.3 Frontend Polish
- Loading states and skeletons
- Error boundaries
- Mobile responsiveness
- Dark mode support

### 6.4 Demo Script
- Walkthrough of graph visualization
- Show question targeting in action
- Display mobile swipe interface
- Show email/SMS examples
- Demonstrate edge discovery

---

## File Structure (New/Modified)

```
backend/
├── alembic/versions/
│   ├── xxx_add_member_edges.py
│   ├── xxx_add_taste_profiles.py
│   ├── xxx_add_event_signals.py
│   ├── xxx_add_question_deliveries.py
│   └── xxx_extend_questions_patterns.py
├── app/
│   ├── agents/
│   │   ├── edge_discovery.py        # NEW
│   │   ├── question_targeting.py    # NEW
│   │   ├── taste_profile.py         # NEW
│   │   ├── event_recommendation.py  # NEW
│   │   └── question_deck.py         # ENHANCED
│   ├── services/
│   │   ├── rova_client.py           # NEW
│   │   └── white_rabbit_client.py   # EXISTING
│   ├── tools/
│   │   ├── graph_tools.py           # NEW
│   │   ├── taste_tools.py           # NEW
│   │   └── event_tools.py           # NEW
│   ├── api/
│   │   ├── endpoints.py             # EXTENDED
│   │   ├── mobile_endpoints.py      # NEW
│   │   └── display_endpoints.py     # NEW
│   └── models.py                    # EXTENDED

frontend/
├── src/
│   ├── pages/
│   │   ├── Graph.tsx                # NEW
│   │   ├── DataModel.tsx            # NEW
│   │   ├── Demo.tsx                 # NEW
│   │   └── MobileQuestion.tsx       # NEW
│   ├── components/
│   │   ├── GraphVisualization.tsx   # NEW
│   │   ├── QuestionCard.tsx         # NEW
│   │   ├── EdgeDetail.tsx           # NEW
│   │   └── TasteProfileCard.tsx     # NEW
│   └── templates/
│       ├── EmailDigest.tsx          # NEW (preview)
│       └── SMSPreview.tsx           # NEW (preview)
```

---

## Success Metrics

### Technical
- [ ] All 6 new database tables created and migrated
- [ ] 4 new agents operational
- [ ] Rova integration syncing events
- [ ] 5+ API endpoints for mobile/display
- [ ] Graph visualization rendering 80+ nodes

### Demo-Ready
- [ ] Graph page shows live community data
- [ ] Mobile swipe interface working
- [ ] Question of the day endpoint serving content
- [ ] Email template preview rendering
- [ ] SMS examples documented

### Non-Deterministic Proof
- [ ] Questions vary based on context (not always same)
- [ ] Edges discovered automatically from data
- [ ] Taste profiles evolve from behavior
- [ ] Randomness factor visible in targeting

---

## Timeline Estimate

| Wave | Description | Complexity | Parallel? |
|------|-------------|------------|-----------|
| 1 | Data Foundation | Medium | No (blocking) |
| 2 | Graph Agents | High | Yes (4 agents) |
| 3 | Rova Integration | Medium | Yes (with Wave 2) |
| 4 | Multi-Channel UI | High | Yes (4 channels) |
| 5 | Graph Visualization | Medium | Yes (with Wave 4) |
| 6 | Polish & Integration | Low | No (final) |

**Recommended Execution:**
1. Wave 1 first (foundation)
2. Waves 2, 3, 4, 5 in parallel (agents working simultaneously)
3. Wave 6 last (integration)

---

*Plan created: February 9, 2026*
*For: White Rabbit Profile Optimizer v2*
