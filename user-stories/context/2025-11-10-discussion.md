Conversation opened. 1 unread message.

Skip to content
Using Gmail with screen readers

1 of 2
WR PRD
Inbox

Annie Lundgren
Attachments
6:43 PM (35 minutes ago)
to me

from last week summary (AI generated from transcripts)


 2 Attachments
  •  Scanned by Gmail



# White Rabbit Concierge Platform - Product Requirements Document

**Version:** 1.0
**Date:** November 17, 2025
**Status:** Draft for Team Review

---

## Executive Summary

The White Rabbit Concierge Platform is an AI-powered system designed to support creator success through intelligent data collection, member matching, and proactive coaching. The platform leverages White Rabbit's high-trust membership model to enable deeper data collection than public platforms, creating synthetic AI profiles that power both query-based and discovery-based agent interactions.

**Core Mission:** Support creators to meaningful achievement through technology, entrepreneurship, and the arts by connecting them to people, resources, and opportunities they need, including those they don't yet know they need.

---

## At-a-Glance Summary

### Three Main Product Tracks

**1. Data Collection & Enrichment**
   - Fixed/curated data: member profiles, resumes, LinkedIn
   - IRL conversations: transcribed meetings with speaker diarization
   - AI chat agent: conversational interviews to supplement manual outreach

**2. White Rabbit Coach (Multi-Agent System)**
   - Query Agent: Answers "who can help me with X?" questions
   - Discovery Agent: Identifies unknown unknowns, connects people to resources they didn't know they needed
   - Synthetic AI profiles from collected data become searchable resource
   - Proactive engagement based on member goals and gaps

**3. Supporting Infrastructure**
   - Table lamp prototype for workspace communication (V1: LED status colors, V2: built-in transcription)
   - Async communication platform trial (Discord alternative)
   - Recording/transcription pipeline (Fireflies for diarization)

### Key Design Principles
- Opt-in data collection at member's pace
- Transparent motivation: supporting creator success
- Respect communication preferences and boundaries
- Personality-aware engagement
- High-trust membership model enables deeper data than public platforms

### Success Metrics
Supporting creators to meaningful achievement (financial sustainability, technology adoption, entrepreneurship, arts intersection, "scenius")

---

## Problem Statement

### Current Challenges

1. **Insufficient Member Data**
   - LinkedIn profiles lack nuance and are often outdated
   - Static, self-reported data doesn't capture the full picture
   - Limited context prevents effective matching and support

2. **Manual Scaling Limitations**
   - Den mother role (Cynthia) cannot scale to give every member personalized attention
   - Members have different engagement appetites and communication preferences
   - Talent identification relies on institutional knowledge

3. **Unknown Unknowns**
   - Members don't always know what questions to ask
   - Potential connections and resources go undiscovered
   - Barriers to success aren't always articulated or understood

### Key Insight

The Mayo Team Composer project demonstrated: **more data points = better AI recommendations**. White Rabbit's high-trust, capped membership model enables richer data collection than public platforms while respecting member boundaries.

---

## Goals & Success Metrics

### Primary Goals

1. **Enable complete, nuanced member profiles** through multi-source data collection
2. **Scale personalized support** beyond manual capacity
3. **Surface unknown unknowns** through proactive AI engagement
4. **Respect member boundaries** while maximizing value delivery

### Success Metrics

- Member profile completion rate
- Quality of AI-generated matches/recommendations (measured by member feedback)
- Engagement with AI coach (conversation frequency, satisfaction)
- Member achievement outcomes (project launches, collaborations formed, revenue generated)
- Opt-in data collection participation rate
- Member retention and satisfaction with support received

---

## User Personas

### The Directed Creator
- Has clear goals and strong directionality
- Willing to put in the work
- Seeks specific expertise or collaborators
- **Needs:** Efficient talent identification, relevant connections

### The Exploratory Creator
- Experimenting and figuring things out
- Open to discovery and serendipity
- May not know what they need yet
- **Needs:** Proactive suggestions, barrier identification, educational resources

### The Privacy-Conscious Member
- Selective about public digital footprint
- Willing to share in trusted environment
- Clear communication boundaries
- **Needs:** Opt-in controls, transparent data use, respected preferences

### The Revenue-Focused Entrepreneur
- Building sustainable/profitable ventures
- Needs business development support
- Limited local resources for revenue generation
- **Needs:** Market connections, monetization strategies, business expertise

---

## Product Architecture: Three Core Elements

## 1. Data Collection & Parsing

### Overview
Multi-track system for building rich, nuanced member profiles that go beyond static LinkedIn data.

### Features

#### Track A: Fixed/Curated Data
- **Member profile completion interface**
  - Structured profile fields
  - Uploaded resumes/portfolios
  - LinkedIn import (as baseline)
  - Self-reported skills, interests, goals
  - Current focus & vision realization needs

- **Profile completion incentives**
  - Show value of complete profiles through AI matching results
  - Filter features by profile completeness
  - Gradual, non-intrusive prompting

#### Track B: IRL Conversation Transcription
- **Recording & transcription pipeline**
  - Granola for basic transcription (current)
  - Fireflies integration for speaker diarization
  - Custom transcript reader API for batch processing
  - Periodic networking calls (Zoom-based, opt-in recording)

- **In-person conversation capture**
  - NFC tap identification for speakers
  - Table lamp V2 with built-in transcription
  - Automatic note distribution to participants
  - Consent-based, opt-in recording

- **Transcript enrichment**
  - Extract interests, expertise, projects, needs
  - Identify collaboration opportunities
  - Update member profiles with behavioral insights
  - Tag topics and themes

#### Track C: AI Interview Agent
- **Conversational profile building**
  - Asynchronous chat interface
  - Personality-aware interview style
  - Progressive disclosure (not all at once)
  - Supplement manual den mother conversations

- **Interview topics**
  - Current focus and goals
  - Skills and expertise (beyond resume)
  - Barriers to achieving creative vision
  - Preferred engagement styles
  - Needs assessment (what's missing?)
  - Personality/working style preferences

- **Behavioral data collection**
  - Log interaction patterns
  - Track question types and focus areas
  - Identify evolving interests over time
  - Feed insights back into profile enrichment

### Data Parsing & Synthesis

- **Keyword extraction:** Identify interests, skills, technologies, domains
- **Semantic profile generation:** Create AI-synthesized member profiles
- **Gap analysis:** Compare stated goals vs. identified needs
- **Cohort clustering:** Group members by interests, goals, complementary skills
- **Network mapping:** Visualize potential connections and collaboration opportunities

---

## 2. Cynthia Den Mother Concierge (White Rabbit Coach)

### Overview
Multi-agent AI system that scales personalized member support, respects boundaries, and proactively surfaces opportunities.

### Agent Architecture

#### Query Agent: "Who Can Help Me?"
**Purpose:** Answer direct questions about talent, expertise, and resources

**Features:**
- Natural language search across synthetic member profiles
- "Who can help me with X?" queries
- Skills-based matching
- Availability/capacity awareness
- Preference-filtered results (respects communication boundaries)

**Example Queries:**
- "Who knows about deploying ML models in production?"
- "Who has experience with sustainable business models?"
- "Who's interested in collaborating on an art/tech project?"

#### Discovery Agent: "Unknown Unknowns"
**Purpose:** Proactively identify barriers, gaps, and opportunities members don't yet see

**Features:**
- Analyze member goals vs. current trajectory
- Identify unstated needs based on similar member journeys
- Surface potential collaborators with complementary skills
- Flag resources, expertise, or conversations that could unblock progress
- Suggest cohort participation based on shared interests

**Proactive Engagement:**
- Periodic check-ins on goal progress
- Suggested connections with context
- "Have you considered...?" prompts
- Barrier identification and resolution suggestions

### Respect for Boundaries & Preferences

- **Engagement appetite controls**
  - Member-set interaction frequency
  - Preferred communication mediums
  - "Heads down" vs. "open to connect" status

- **Communication style personalization**
  - Personality assessment (Myers-Briggs, Enneagram, etc.)
  - Adapt agent tone and approach
  - Respect for different working/networking styles

- **Transparent motivation**
  - Clear explanation of data use
  - Visible AI reasoning ("I'm suggesting this because...")
  - Member control over profile visibility and sharing

### Coach Interaction Model

- **Password-protected member portal**
  - Synthetic AI profiles as searchable resource
  - Chat interface with both agents
  - Conversation history and insights
  - Connection recommendations with context

- **Continuous learning loop**
  - Log all agent interactions
  - Feed query patterns back into profile enrichment
  - Improve matching algorithms based on successful connections
  - Refine discovery patterns based on member outcomes

---

## 3. How to Dev Together (AI Team Coding Framework)

### Overview
Infrastructure and tools enabling collaborative development of the platform itself, leveraging AI-assisted coding.

### Features

#### Development Infrastructure
- **AI coding agent integration**
  - GitHub Copilot or similar tools
  - Shared coding standards and practices
  - Collaborative prompt engineering for agents

#### Team Collaboration Tools
- **Asynchronous communication**
  - Trial Discord alternative (new platform from Twitter alum)
  - Low attack surface, security-conscious
  - Structured channels for: features, bugs, ideas, demos

- **Documentation & knowledge sharing**
  - Living PRD (this document)
  - Technical architecture docs
  - Decision logs and rationale
  - Coaching prompts and best practices library

#### Prototyping & Testing
- **Rapid experimentation**
  - Table lamp V1 prototype (LED status indicator)
  - USB heart lantern testing for workspace status
  - Quick feedback loops with member testing group

---

## Technical Requirements

### Data Collection Infrastructure

- **Transcription services**
  - Fireflies API integration for diarization
  - Custom transcript processing pipeline
  - Secure storage for sensitive conversations
  - Speaker identification and attribution

- **Profile database**
  - Structured fields for fixed data
  - Unstructured storage for transcripts, interview logs
  - Vector embeddings for semantic search
  - Versioning for profile evolution over time

- **Data ingestion APIs**
  - LinkedIn import
  - Resume/document parsing
  - Transcript upload and processing
  - Manual data entry forms

### AI Agent Infrastructure

- **LLM integration**
  - Multi-agent orchestration
  - Context management for long conversations
  - Personality/style adaptation layer
  - Query routing between agents

- **Synthetic profile generation**
  - Semantic extraction from raw data
  - Profile summarization and synthesis
  - Keyword/interest tagging
  - Confidence scoring on extracted data

- **Matching & recommendation engine**
  - Vector similarity search
  - Skills/needs complementarity scoring
  - Graph-based network analysis
  - Availability and preference filtering

### Security & Privacy

- **Authentication & access control**
  - Password-protected member portal
  - Role-based access (members, admins, agents)
  - Audit logging for data access

- **Data governance**
  - Opt-in consent tracking
  - Data retention policies
  - Member control over profile visibility
  - GDPR/privacy compliance considerations

---

## Design Principles

1. **Opt-in at member's pace** - No forced data collection; gradual, value-driven participation
2. **Transparent motivation** - Always clear why we're asking and how data will be used
3. **Respect boundaries** - Honor communication preferences, engagement appetite, privacy needs
4. **Proactive but not pushy** - Surface opportunities without overwhelming
5. **High trust environment** - Leverage White Rabbit's capped, vetted membership model
6. **Personality-aware** - Adapt to different working styles and preferences
7. **Value exchange** - Data sharing must provide clear member benefit
8. **Scenius enablement** - Create conditions for collective genius, not forced outcomes

---

## Phased Roadmap

### Phase 1: Foundation (Current)
- [ ] Audit existing member profile data for completeness
- [ ] Identify top 20 members with complete-enough profiles for initial testing
- [ ] Set up Fireflies transcription pipeline
- [ ] Draft coaching prompt library and interview questions
- [ ] Trial async communication platform with core team
- [ ] Test table lamp V1 prototype (USB heart lantern)

### Phase 2: Data Collection MVP
- [ ] Build profile completion interface with incentive messaging
- [ ] Deploy AI interview agent (Track C) with 10 beta members
- [ ] Set up monthly opt-in networking calls with recording
- [ ] Create transcript processing pipeline for enrichment
- [ ] Develop coaching prompts and best practices framework

### Phase 3: Query Agent MVP
- [ ] Build synthetic profile generation system
- [ ] Create searchable member directory with AI profiles
- [ ] Deploy query agent with natural language search
- [ ] Member portal for coach access (password-protected)
- [ ] Collect feedback on match quality and relevance

### Phase 4: Discovery Agent & Proactive Engagement
- [ ] Analyze member goal patterns and success trajectories
- [ ] Build barrier identification and opportunity surfacing logic
- [ ] Deploy discovery agent with proactive suggestions
- [ ] Implement engagement preference controls
- [ ] Personality assessment and style adaptation

### Phase 5: Scale & Refinement
- [ ] Expand to full membership base
- [ ] Continuous learning loop for agent improvement
- [ ] Advanced cohort clustering and project formation
- [ ] Table lamp V2 with built-in transcription
- [ ] Integration with broader White Rabbit platform initiatives

---

## Open Questions & Decisions Needed

1. **Data retention:** How long do we keep transcripts? When do we anonymize/delete?
2. **Profile visibility:** Can members see each other's synthetic profiles, or only query results?
3. **Agent personality:** Should we name the agents? Give them distinct personalities?
4. **Monetization (if any):** Is this a member benefit, or potential standalone product?
5. **External data sources:** Do we scrape Twitter, YouTube, podcasts, or only use consented data?
6. **Human in the loop:** When should Cynthia/staff intervene vs. full agent autonomy?
7. **Failure mode:** How do we handle bad matches, inappropriate suggestions, or member complaints?

---

## Team Roles & Responsibilities

- **Product/Strategy:** Define features, prioritize roadmap, ensure alignment with White Rabbit mission
- **Engineering:** Build data pipelines, AI agents, member portal, infrastructure
- **Design/UX:** Member-facing interfaces, agent personality/tone, interaction flows
- **Coaching/Content:** Develop interview prompts, best practices, personality frameworks
- **Community/Operations:** Member onboarding, feedback collection, manual support where needed

---

## Appendix: Reference Materials

- **Meeting transcript:** [Granola Notes](https://notes.granola.ai/d/c3a1839a-a6ca-40d2-9f25-01db2d3a0d82)
- **Prior art:** Mayo Team Composer (skills-based team assembly)
- **Inspiration:** "Scenius" concept (Brian Eno) - collective genius through space and community
- **Theoretical foundation:** Kurt Lewin - "Behavior is a function of personality and space"

---

**Next Review:** [Date TBD] - Team feedback on priorities, phasing, and open questions
prd.md
Displaying prd.md.
