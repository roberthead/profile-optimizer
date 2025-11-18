# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Profile Optimizer is a conversational AI agent that enriches member profile data for the White Rabbit Ashland community (http://whiterabbitashland.com).

**Core Purpose:** Illuminate connections within the community to foster collaboration, build better events and cohorts, and ultimately help creators achieve meaningful success through technology, entrepreneurship, and the arts.

**Narrative Position:** Setting an ethical example for how we move into the future with new technology and innovation - responsible, transparent, and human-centered AI development.

## Current Development Focus (Nov 2024)

**Initial Feature:** Profile Optimizer Agent
- Evaluates current profile completeness for existing ~80 members
- Has conversational interviews to gather rich data
- Can analyze LinkedIn/social profiles (only if user provides)
- Suggests profile improvements and content
- **User always approves** what gets published (AI as draft, never final)

**Design Decision:** Start with enriching existing member profiles (not new user onboarding) to build a rich dataset that enables future features.

## Ethical Principles (NON-NEGOTIABLE)

These principles override all other concerns and must be followed in every implementation decision:

1. **Opt-in at member's pace** - No forced data collection; user decides what to share
2. **AI suggests, human approves** - No AI-generated content becomes final without user consent
3. **Transparent visibility** - Always disclose who can see collected data
4. **Respect boundaries** - Honor communication preferences and engagement appetite
5. **High-trust environment** - Leverage White Rabbit's capped membership model responsibly
6. **Personality-aware** - Adapt to different working styles and preferences
7. **Transparent motivation** - Always clear why data is being collected and how it will be used

**Privacy Example:** If a user provides their LinkedIn in conversation with the agent, that's different from publishing it on their public profile. The agent should distinguish between private conversation context vs. public profile data.

## The Bigger Vision (Future Phases)

While we're starting with the profile optimizer, the long-term vision includes:

### Three Product Tracks
1. **Data Collection & Enrichment** - Multi-source profile building (fixed data, IRL transcriptions, AI interviews)
2. **White Rabbit Coach** - Multi-agent system with Query Agent ("who can help me with X?") and Discovery Agent (proactive barrier identification, unknown unknowns)
3. **Collaborative Dev Infrastructure** - How to build AI products together as a team

### Success Metrics
- Supporting creators to meaningful achievement (financial sustainability, technology adoption, scenius)
- Quality of AI-generated matches/recommendations
- Member profile completion and richness
- Engagement with AI coach
- Opt-in participation rate

## Key Design Constraints

1. **Start small, prove value** - Pick one feature, build it, reflect, iterate
2. **Different people, different needs** - Some fill out forms, some chat, some upload docs - support all patterns
3. **Community over isolation** - Technology should bring people together, not enable further isolation
4. **Collaboration is messy** - No hierarchy, democratic decision-making, embrace the messiness

## Project Structure

```
user-stories/
  active/
    profile-agent.md - Original user story
    2025-11-10-discussion.md - PRD synthesis from week 1
    2025-11-17-discussion.md - Implementation discussion transcript
```

## Development Philosophy

**The Tension:** The team includes both "move fast and break things" and "research thoroughly first" developers. Both approaches are valid.

**The Resolution:**
- Do enough research/planning to define clear requirements and narrow guardrails
- Build with AI assistance, but don't vibe code without direction
- Short iteration cycles (not 3 months, not 1 hour - find the middle)
- Test hypotheses quickly, reflect on what works

**Collaboration Model:**
- This project itself is an experiment in how to collaborate on AI products
- Weekly sessions to learn, build, and grow skills together
- Open source contribution back to White Rabbit community
- Different expertise levels welcome (learning Git, first group project, etc.)

## Critical Context for AI Development

**Why more data = better:** Mayo Team Composer demonstrated that richer data points lead to better AI recommendations. White Rabbit's high-trust, capped membership model enables deeper data collection than public platforms.

**The Den Mother Problem:** Cynthia currently does manual member support/interviews - this doesn't scale. The agent should extend her capacity, not replace the human touch.

**Unknown Unknowns:** Members don't always know what questions to ask or what resources they need. The eventual Discovery Agent should proactively surface opportunities.

## What We're NOT Building (Yet)

- New member onboarding flow
- Public-facing features
- Invasive data scraping without consent
- Fully autonomous AI (human always in the loop)
- Features that work without rich profile data

## Tech Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL (local)
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **LLM:** Anthropic Claude (via SDK)
- **Web Scraping:** BeautifulSoup + LLM web search capabilities

### Frontend
- **Language:** TypeScript
- **Framework:** React
- **Data Fetching:** TanStack Query (React Query)
- **Build Tool:** Vite
- **Deployment Target:** Custom web app, eventual subdomain integration with whiterabbitashland.com

### Development Approach
- **Simple over complex:** Raw Anthropic SDK (no LangChain/complex frameworks)
- **Local development:** Docker Compose for Postgres
- **API-first:** Clean REST API boundaries between frontend/backend
- **Iterative:** Start simple, add complexity as needed

## Commands

Development commands will be added as the project is built out.

**Current Status:** Planning phase - no build/test infrastructure exists yet.
