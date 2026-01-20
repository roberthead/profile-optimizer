"""LLM-backed agent for generating insightful question decks."""

import json
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic

from app.models import Member, QuestionDeck, Question, QuestionCategory, QuestionType
from app.core.config import settings
from app.tools.question_tools import (
    get_community_profile_analysis,
    get_member_gaps,
    get_active_patterns,
    GET_COMMUNITY_ANALYSIS_TOOL,
    GET_MEMBER_GAPS_TOOL,
    GET_ACTIVE_PATTERNS_TOOL,
    SAVE_QUESTION_DECK_TOOL,
)


SYSTEM_PROMPT = """You are a question designer for White Rabbit Ashland - a creative community focused on technology, entrepreneurship, and the arts.

Your job is to generate thoughtful, engaging questions that help surface interesting insights about community members. These questions will be used in gamified profile-building experiences.

## Design Principles

1. **Surface the interesting**: Don't ask about job titles - ask what makes someone light up when they talk about their work.

2. **Enable connection**: Questions should help members discover unexpected commonalities with others.

3. **Vary question depth**: Include a MIX of depths in every deck - not everything should require deep reflection:
   - Level 1 (Easy): Quick, fun, approachable - answerable in 10 seconds (aim for ~40% of questions)
   - Level 2 (Medium): Thoughtful but not too personal - a sentence or two (aim for ~40% of questions)
   - Level 3 (Deep): Reflective, vulnerable, meaningful - requires real thought (aim for ~20% of questions)

   IMPORTANT: Decks heavy on Level 3 questions feel exhausting. Keep it light and playful overall.

4. **Be specific over generic**: "What's a problem you've been obsessed with solving?" beats "What are you working on?"

5. **Create narrative hooks**: Good questions lead to stories, not just facts.

## Question Categories

- **origin_story**: Where they come from, how they got here
- **creative_spark**: What inspires them, drives their creativity
- **collaboration**: How they work with others, what they seek in collaborators
- **future_vision**: Where they're headed, aspirations
- **community_connection**: What they bring to/seek from the community
- **hidden_depths**: Unexpected skills, interests, experiences
- **impact_legacy**: What they want to create/leave behind

## Question Types

Generate a variety of question TYPES to keep the experience engaging. Aim for this mix:
- **free_form** (~40%): Open-ended questions requiring text responses. Best for deeper exploration.
- **multiple_choice** (~25%): Select from 3-5 predefined options. Quick, fun, and easy to answer. Must include "options" array.
- **yes_no** (~15%): Simple binary questions. Great for quick engagement and filtering.
- **fill_in_blank** (~20%): Complete a sentence. Fun and reveals personality. Must include "blank_prompt" with ___ marking the blank.

Examples:
- free_form: "What's a skill you have that would surprise most people?"
- multiple_choice: "What's your ideal collaboration style?" with options: ["Deep focus with one partner", "Small tight-knit team", "Large diverse group", "Solo with occasional feedback"]
- yes_no: "Have you ever started a business?"
- fill_in_blank: blank_prompt: "The thing I could talk about for hours is ___"

IMPORTANT: Vary the types! Don't make an entire deck of free_form questions - mix in quick multiple_choice and yes_no questions to keep it light.

## Output Format

When generating questions, provide:
- question_text: The actual question
- question_type: One of: free_form, multiple_choice, yes_no, fill_in_blank
- options: (required for multiple_choice) Array of 3-5 answer choices
- blank_prompt: (required for fill_in_blank) Sentence with ___ for the blank
- category: One of the categories above
- difficulty_level: 1-3
- purpose: Why this question is valuable (1 sentence)
- follow_up_prompts: 1-2 probing follow-ups if the initial answer is brief
- potential_insights: What you might learn from the answer
- related_profile_fields: Which profile fields this might help fill (bio, skills, interests, etc.)

## Context Awareness

You will receive FULL PROFILE DATA for all community members. Use this rich context to:
- Reference specific themes, skills, and interests actually present in the community
- Create questions that could surface connections between members (e.g., if several members mention "AI" and "music", ask about creative uses of technology)
- Notice patterns in how members describe themselves and ask questions that dig deeper into those patterns
- Identify under-explored areas and generate questions that could reveal hidden commonalities
- Generate questions that feel relevant to THIS specific community, not generic icebreakers

IMPORTANT: Avoid generic questions like "What are your hobbies?" - instead, craft questions informed by what you see in the actual profiles. For example, if you notice many members are entrepreneurs, ask about the specific challenges of building something in a small town.

When generating for a specific member, personalize based on their existing profile and gaps.

## Pattern-Informed Question Generation

You have access to DISCOVERED COMMUNITY PATTERNS - these are insights the pattern finder has already identified about the community (skill clusters, interest themes, collaboration opportunities, etc.).

Each pattern includes:
- **name/description**: What the pattern represents
- **category**: Type of pattern (skill_cluster, interest_theme, collaboration_opportunity, community_strength, cross_domain)
- **member_count**: How prevalent this pattern is
- **evidence**: Supporting data like skill/interest frequencies
- **question_prompts**: Pre-suggested questions to explore this pattern

When patterns are available, use them to:
1. **Explore pattern depths**: Generate questions that help understand WHY these patterns exist and what they mean to members
2. **Surface hidden connections**: Create questions that could reveal additional members who fit existing patterns
3. **Bridge patterns**: Ask questions that might connect members across different patterns
4. **Validate patterns**: Design questions that test whether patterns hold deeper meaning or are surface-level

IMPORTANT: Patterns are a starting point, not a constraint. Use them as inspiration but also generate novel questions that go beyond the pre-suggested prompts. The goal is questions that feel both pattern-aware AND fresh."""


class QuestionDeckAgent:
    """LLM-backed agent that generates insightful question decks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-opus-4-5"

    async def generate_global_deck(
        self,
        deck_name: str = "Community Discovery Deck",
        description: Optional[str] = None,
        num_questions: int = 20,
        focus_categories: Optional[List[str]] = None
    ) -> dict[str, Any]:
        """
        Generate a global question deck by analyzing all member profiles.

        Args:
            deck_name: Name for the generated deck
            description: Optional custom description/purpose for the deck
            num_questions: Target number of questions to generate
            focus_categories: Optional list of categories to focus on

        Returns:
            Dict with deck_id, questions generated, and metadata
        """
        # Build the prompt
        category_guidance = ""
        if focus_categories:
            category_guidance = f"\n\nFocus especially on these categories: {', '.join(focus_categories)}"

        custom_purpose = ""
        if description:
            custom_purpose = f"""

IMPORTANT - Custom deck purpose provided by the user:
\"\"\"{description}\"\"\"

Generate questions that specifically serve this purpose. The description above should guide the theme, tone, and focus of all questions in the deck."""

        user_message = f"""Please generate a question deck for the White Rabbit community.

First, gather context by using these tools:
1. get_community_profile_analysis - to understand the current state of member profiles
2. get_active_patterns - to retrieve discovered community patterns (skill clusters, interest themes, collaboration opportunities, etc.)
{custom_purpose}
Then, generate approximately {num_questions} insightful questions that:
1. Help fill common gaps you discover in the analysis
2. Surface interesting insights about members that aren't captured in standard profile fields
3. Explore and deepen discovered community patterns
4. Create opportunities for pattern-related members to connect
5. Balance across difficulty levels and categories{category_guidance}

When incorporating patterns, use them as inspiration to craft questions that feel both pattern-aware AND fresh. Don't just repeat the pre-suggested question_prompts from patterns - build on them creatively.

After generating the questions, use save_question_deck to persist them with:
- Name: "{deck_name}"
- Description: {f'"{description}"' if description else 'A description explaining the deck\'s purpose, what analysis informed it, and which patterns it explores'}
- The complete list of questions"""

        return await self._execute_with_tools(user_message)

    async def generate_personalized_deck(
        self,
        member_id: int,
        num_questions: int = 10
    ) -> dict[str, Any]:
        """
        Generate a personalized question deck for a specific member.

        Args:
            member_id: The member to generate questions for
            num_questions: Target number of questions

        Returns:
            Dict with deck_id, questions generated, and metadata
        """
        # Get member name for context
        result = await self.db.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError(f"Member with id {member_id} not found")

        member_name = f"{member.first_name or ''} {member.last_name or ''}".strip() or member.email

        user_message = f"""Please generate a personalized question deck for member {member_name} (ID: {member_id}).

First, gather context by using these tools:
1. get_member_gaps - to understand their current profile state and identify opportunities
2. get_active_patterns - to see which community patterns they might relate to or could be connected with

Then, generate approximately {num_questions} questions tailored to:
1. Fill their specific profile gaps
2. Draw out interesting aspects of who they are
3. Build on what's already in their profile (use it as context, not repetition)
4. Explore their connection to discovered community patterns
5. Help them see potential collaborations with other pattern-related members

After generating the questions, use save_question_deck to persist them with:
- Name: "Personal Discovery - {member_name}"
- A description explaining what gaps, opportunities, and pattern connections this deck addresses
- The complete list of questions
- member_id: {member_id}"""

        return await self._execute_with_tools(user_message)

    async def refine_deck(
        self,
        deck_id: int,
        feedback: str
    ) -> dict[str, Any]:
        """
        Refine an existing deck based on feedback.

        Args:
            deck_id: The deck to refine
            feedback: User feedback about what to improve

        Returns:
            Dict with updated deck information
        """
        # Get existing deck
        result = await self.db.execute(
            select(QuestionDeck).where(QuestionDeck.id == deck_id)
        )
        deck = result.scalar_one_or_none()
        if not deck:
            raise ValueError(f"Deck with id {deck_id} not found")

        # Get existing questions
        result = await self.db.execute(
            select(Question).where(Question.deck_id == deck_id).order_by(Question.order_index)
        )
        existing_questions = result.scalars().all()

        questions_json = [
            {
                "id": q.id,
                "question_text": q.question_text,
                "category": q.category.value,
                "difficulty_level": q.difficulty_level,
                "purpose": q.purpose,
            }
            for q in existing_questions
        ]

        member_id_str = f"member_id: {deck.member_id}" if deck.member_id else "null (global deck)"

        user_message = f"""Please help refine the question deck "{deck.name}".

Current questions in the deck:
{json.dumps(questions_json, indent=2)}

Feedback to address:
{feedback}

Based on this feedback:
1. Analyze what changes would improve the deck
2. Generate a revised deck that addresses the feedback
3. Save the updated deck (this will create a new version)

Use save_question_deck to save the refined deck with:
- Same name but updated description mentioning the refinement
- The revised questions
- {member_id_str}"""

        return await self._execute_with_tools(user_message)

    async def _execute_with_tools(self, user_message: str) -> dict[str, Any]:
        """Execute a conversation with tool use."""
        tools = [GET_COMMUNITY_ANALYSIS_TOOL, GET_MEMBER_GAPS_TOOL, GET_ACTIVE_PATTERNS_TOOL, SAVE_QUESTION_DECK_TOOL]
        messages = [{"role": "user", "content": user_message}]

        result = {
            "success": False,
            "deck_id": None,
            "questions_generated": 0,
            "analysis_context": None,
            "response_text": "",
        }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Handle tool use in a loop
        while response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_result = await self._execute_tool(block.name, block.input, result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result),
                    })

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

        # Extract final response text
        for block in response.content:
            if hasattr(block, "text"):
                result["response_text"] = block.text
                break

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        result: dict
    ) -> dict:
        """Execute a tool and return the result."""

        if tool_name == "get_community_profile_analysis":
            analysis = await get_community_profile_analysis(self.db)
            result["analysis_context"] = analysis
            return analysis

        elif tool_name == "get_member_gaps":
            member_id = tool_input.get("member_id")
            gaps = await get_member_gaps(self.db, member_id)
            return gaps

        elif tool_name == "get_active_patterns":
            patterns = await get_active_patterns(self.db)
            result["patterns_context"] = patterns
            return patterns

        elif tool_name == "save_question_deck":
            deck = await self._save_deck(tool_input)
            result["success"] = True
            result["deck_id"] = deck.id
            result["questions_generated"] = len(tool_input.get("questions", []))
            return {
                "success": True,
                "deck_id": deck.id,
                "message": f"Saved deck with {result['questions_generated']} questions"
            }

        return {"error": f"Unknown tool: {tool_name}"}

    async def _save_deck(self, tool_input: dict) -> QuestionDeck:
        """Save a question deck to the database."""
        deck = QuestionDeck(
            name=tool_input["name"],
            description=tool_input.get("description", ""),
            member_id=tool_input.get("member_id"),
            generation_context=tool_input.get("generation_context"),
        )
        self.db.add(deck)
        await self.db.flush()  # Get the deck ID

        questions = tool_input.get("questions", [])
        for idx, q in enumerate(questions):
            # Parse question type, defaulting to free_form
            question_type_str = q.get("question_type", "free_form")
            question_type = QuestionType(question_type_str)

            question = Question(
                deck_id=deck.id,
                question_text=q["question_text"],
                category=QuestionCategory(q["category"]),
                question_type=question_type,
                options=q.get("options", []) if question_type == QuestionType.MULTIPLE_CHOICE else [],
                blank_prompt=q.get("blank_prompt") if question_type == QuestionType.FILL_IN_BLANK else None,
                difficulty_level=q.get("difficulty_level", 1),
                estimated_time_minutes=q.get("estimated_time_minutes", 2),
                purpose=q["purpose"],
                follow_up_prompts=q.get("follow_up_prompts", []),
                potential_insights=q.get("potential_insights", []),
                related_profile_fields=q.get("related_profile_fields", []),
                order_index=idx,
            )
            self.db.add(question)

        await self.db.commit()
        await self.db.refresh(deck)
        return deck
