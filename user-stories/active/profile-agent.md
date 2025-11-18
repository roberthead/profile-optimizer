# Project: Profile Optimizer Agent

## Background

http://whiterabbitashland.com

Illuminate Connections
why? in order to build better events and cohorts
why? in order to foster collaboration
why? in order for our community to thrive
	why? to create a more human(e) world

setting the narrative for how we move into the future with new technology and innovation

supported by rich profile data

## User Story

**As a** White Rabbit member
**I want** an AI agent to help me build a rich, complete profile
**So that** I can be more easily discovered by other members for collaboration, and discover others with complementary skills and interests

### Acceptance Criteria

The profile optimizer agent:
- Can read my existing White Rabbit profile and evaluate completeness
- Can have conversational interviews with me to gather information
- Can optionally analyze my LinkedIn or social profiles (only if I provide the URLs in conversation)
- Suggests improvements and additions to my profile based on collected data
- **Requires my approval** before any suggestion becomes part of my public profile
- Distinguishes between private conversation context and public profile data

### Initial Implementation Focus

- Target: Enrich profiles for existing ~80 White Rabbit members (not new user onboarding)
- Interface: Web-based chat interface
- Goal: Build rich dataset to enable future features (cohort building, query agent, discovery agent)

## Data Sources (All Opt-in)

- Agent chat conversations (private)
- LinkedIn/social profiles (only if user provides URL)
- Uploaded documents (future)
- Audio recording transcriptions (future)

## Ethical Principles (Non-Negotiable)

1. **Opt-in at member's pace** - No forced data collection
2. **AI suggests, human approves** - No AI-generated content becomes final without user consent
3. **Transparent visibility** - Always disclose who can see collected data
4. **User decides what to share** - Member has full control
5. **Respect boundaries** - Honor communication preferences and engagement appetite
6. **Privacy distinction** - What's shared in conversation ≠ what's published on profile

## Tech Stack

**Backend:** Python/FastAPI + PostgreSQL
**Frontend:** TypeScript/React (TanStack Query)
**LLM:** Anthropic Claude
**Approach:** Simple, raw SDK (no complex frameworks)
**Deployment:** Custom web app, eventual subdomain of whiterabbitashland.com

## Notes

- Didn't expect enrollment questions to be publicly posted (privacy concern)
- Mayo Team Composer insight: more data points = better AI recommendations
- Cynthia's "den mother" role currently doesn't scale - agent should extend, not replace
- This project is also an experiment in collaborative AI development
