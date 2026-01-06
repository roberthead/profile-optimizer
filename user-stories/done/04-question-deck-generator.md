# User Story 4: Question Deck Generator Agent

## User Story

**As a** White Rabbit admin/developer
**I want to** generate insightful questions by analyzing all member profiles
**So that** we have a "deck" of engaging questions to use for gamified profile enrichment

## Description

Build an agent that examines all member profiles collectively to generate a curated list of questions. These questions are designed to surface interesting insights about members, somewhat independent of specific profile fields. The questions can be used in future gamified experiences to learn more about members and suggest profile improvements.

## Acceptance Criteria

### Given the agent has access to all member profiles
- [x] When it generates a global deck
- [x] Then it analyzes patterns across all profiles (skills, interests, gaps)
- [x] And it generates questions balanced across categories
- [x] And questions are stored in the database for later use

### Given a specific member needs personalized questions
- [x] When the agent generates a personalized deck
- [x] Then it analyzes that member's specific profile gaps
- [x] And it generates questions tailored to their missing information
- [x] And questions build on what's already in their profile

### Given an existing deck needs improvement
- [x] When feedback is provided to the agent
- [x] Then it refines the deck based on that feedback
- [x] And a new version of the deck is created

### Given questions are generated
- [x] Then each question has a category (origin_story, creative_spark, etc.)
- [x] And each question has a difficulty level (1-3)
- [x] And each question has a purpose explaining why it's valuable
- [x] And questions include follow-up prompts for deeper exploration

## Technical Notes

### Question Categories
- **origin_story**: Where they come from, how they got here
- **creative_spark**: What inspires them, drives creativity
- **collaboration**: How they work with others, what they seek
- **future_vision**: Where they're headed, aspirations
- **community_connection**: What they bring to/seek from community
- **hidden_depths**: Unexpected skills, interests, experiences
- **impact_legacy**: What they want to create/leave behind

### Database Models
- `QuestionDeck`: Collection of questions (global or member-specific)
- `Question`: Individual question with metadata
- `QuestionResponse`: Future tracking of member answers

### API Endpoints
```
POST /api/v1/questions/deck/generate-global
POST /api/v1/questions/deck/generate-personal
POST /api/v1/questions/deck/refine
GET  /api/v1/questions/decks
GET  /api/v1/questions/deck/{id}
```

### Agent Tools
- `get_community_profile_analysis`: Analyze all profiles for patterns
- `get_member_gaps`: Analyze specific member's profile gaps
- `save_question_deck`: Persist generated deck to database

## Ethical Considerations

- Questions should be thoughtful, not interrogating
- Questions respect different comfort levels (difficulty levels)
- Questions designed to surface connections, not extract data
- No automatic profile updates - questions inform future suggestions

## Implementation Order

1. [x] Database: Add QuestionCategory enum, QuestionDeck, Question, QuestionResponse models
2. [x] Database: Create and run Alembic migration
3. [x] Tools: Create question_tools.py with analysis functions
4. [x] Agent: Create QuestionDeckAgent
5. [x] API: Add endpoints to endpoints.py
6. [x] Tests: Create unit and integration tests (17 tests passing)

## Out of Scope

- UI for displaying/answering questions (future story)
- Automatic profile updates from answers (future story)
- Multi-language question support
- Question analytics/effectiveness tracking

## Success Metrics

- Agent can generate 20+ diverse questions for global deck
- Questions span all 7 categories
- Personalized decks identify member-specific gaps
- Tests pass for agent functionality
