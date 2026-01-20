"""Tools for question generation and pattern discovery."""

from collections import Counter
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Member, Pattern, PatternCategory


async def get_community_profile_analysis(db: AsyncSession) -> dict[str, Any]:
    """
    Analyze all member profiles to understand community patterns.
    Returns both aggregated insights AND full member profiles for rich context.
    """
    result = await db.execute(
        select(Member).where(Member.membership_status.notin_(['cancelled', 'expired']))
    )
    members = result.scalars().all()

    total_members = len(members)

    # Analyze field completion rates
    field_stats = {
        "bio": {"filled": 0, "total": total_members, "avg_length": 0},
        "role": {"filled": 0, "total": total_members},
        "company": {"filled": 0, "total": total_members},
        "location": {"filled": 0, "total": total_members},
        "website": {"filled": 0, "total": total_members},
        "skills": {"filled": 0, "total": total_members, "avg_count": 0},
        "interests": {"filled": 0, "total": total_members, "avg_count": 0},
        "prompt_responses": {"filled": 0, "total": total_members, "avg_count": 0},
    }

    bio_lengths = []
    skill_counts = []
    interest_counts = []
    all_skills = []
    all_interests = []

    # Build full member profiles for context
    member_profiles = []

    for member in members:
        if member.bio and member.bio.strip():
            field_stats["bio"]["filled"] += 1
            bio_lengths.append(len(member.bio))
        if member.role and member.role.strip():
            field_stats["role"]["filled"] += 1
        if member.company and member.company.strip():
            field_stats["company"]["filled"] += 1
        if member.location and member.location.strip():
            field_stats["location"]["filled"] += 1
        if member.website and member.website.strip():
            field_stats["website"]["filled"] += 1
        if member.skills:
            field_stats["skills"]["filled"] += 1
            skill_counts.append(len(member.skills))
            all_skills.extend(member.skills)
        if member.interests:
            field_stats["interests"]["filled"] += 1
            interest_counts.append(len(member.interests))
            all_interests.extend(member.interests)
        if member.prompt_responses:
            field_stats["prompt_responses"]["filled"] += 1

        # Add full profile for this member
        member_name = f"{member.first_name or ''} {member.last_name or ''}".strip()
        member_profiles.append({
            "id": member.id,
            "name": member_name or "Anonymous",
            "bio": member.bio,
            "role": member.role,
            "company": member.company,
            "location": member.location,
            "skills": member.skills or [],
            "interests": member.interests or [],
            "prompt_responses": member.prompt_responses or {},
            "all_traits": member.all_traits or [],
        })

    # Calculate averages
    if bio_lengths:
        field_stats["bio"]["avg_length"] = sum(bio_lengths) / len(bio_lengths)
    if skill_counts:
        field_stats["skills"]["avg_count"] = sum(skill_counts) / len(skill_counts)
    if interest_counts:
        field_stats["interests"]["avg_count"] = sum(interest_counts) / len(interest_counts)

    # Find common and unique skills/interests
    skill_frequency = Counter(all_skills)
    interest_frequency = Counter(all_interests)

    return {
        "total_active_members": total_members,
        "field_completion_rates": {
            field: {
                "rate": round(stats["filled"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
                **stats
            }
            for field, stats in field_stats.items()
        },
        "common_skills": skill_frequency.most_common(20),
        "common_interests": interest_frequency.most_common(20),
        "unique_skills": [s for s, c in skill_frequency.items() if c == 1][:20],
        "unique_interests": [i for i, c in interest_frequency.items() if c == 1][:20],
        "member_profiles": member_profiles,
    }


async def get_member_gaps(db: AsyncSession, member_id: int) -> dict[str, Any]:
    """
    Analyze a specific member's profile to identify gaps and opportunities.
    """
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()

    if not member:
        return {"error": f"Member {member_id} not found"}

    gaps = []
    opportunities = []

    # Check each field
    if not member.bio or len(member.bio) < 50:
        gaps.append({
            "field": "bio",
            "issue": "Missing or very short bio",
            "opportunity": "Tell your story - what brings you to White Rabbit?"
        })

    if not member.skills:
        gaps.append({
            "field": "skills",
            "issue": "No skills listed",
            "opportunity": "Help others discover what you can contribute"
        })
    elif len(member.skills) < 3:
        opportunities.append({
            "field": "skills",
            "note": "Only a few skills listed",
            "opportunity": "Are there hidden talents you haven't shared?"
        })

    if not member.interests:
        gaps.append({
            "field": "interests",
            "issue": "No interests listed",
            "opportunity": "What gets you excited? Help us find your people."
        })

    if not member.role:
        gaps.append({
            "field": "role",
            "issue": "No role/title",
            "opportunity": "How do you describe what you do?"
        })

    if not member.prompt_responses:
        opportunities.append({
            "field": "prompt_responses",
            "note": "No prompt responses",
            "opportunity": "These reveal personality - a great way to stand out"
        })

    if not member.location:
        opportunities.append({
            "field": "location",
            "note": "No location listed",
            "opportunity": "Help local members find you"
        })

    return {
        "member_id": member_id,
        "member_name": f"{member.first_name or ''} {member.last_name or ''}".strip() or member.email,
        "current_profile": {
            "bio": member.bio[:200] if member.bio else None,
            "role": member.role,
            "company": member.company,
            "skills": member.skills or [],
            "interests": member.interests or [],
            "location": member.location,
        },
        "gaps": gaps,
        "opportunities": opportunities,
    }


# Tool definitions for Claude API
GET_COMMUNITY_ANALYSIS_TOOL = {
    "name": "get_community_profile_analysis",
    "description": """Analyze all member profiles to understand community patterns. Returns:
- Field completion rates and statistics
- Common and unique skills/interests across the community
- FULL PROFILES for every active member including: name, bio, role, company, location, skills, interests, prompt_responses, and all_traits

Use this rich context to generate specific, personalized questions that reference actual themes, skills, and interests present in the community. Avoid generic questions - instead create questions informed by what members have actually shared.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


GET_MEMBER_GAPS_TOOL = {
    "name": "get_member_gaps",
    "description": "Analyze a specific member's profile to identify gaps and opportunities for enrichment. Use this when generating personalized questions for a member.",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The ID of the member whose profile to analyze"
            }
        },
        "required": ["member_id"]
    }
}


SAVE_QUESTION_DECK_TOOL = {
    "name": "save_question_deck",
    "description": "Save a generated question deck to the database. Use this after generating questions to persist them.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name for this question deck"
            },
            "description": {
                "type": "string",
                "description": "Description of this deck's purpose and focus"
            },
            "member_id": {
                "type": "integer",
                "description": "Optional: If provided, this is a personalized deck for this member. If null/omitted, this is a global deck."
            },
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_text": {"type": "string", "description": "The question to ask"},
                        "question_type": {
                            "type": "string",
                            "enum": ["free_form", "multiple_choice", "yes_no", "fill_in_blank"],
                            "description": "Type of question: free_form (open text), multiple_choice (select from options), yes_no (binary), fill_in_blank (complete a sentence)"
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required for multiple_choice: list of 3-5 answer options"
                        },
                        "blank_prompt": {
                            "type": "string",
                            "description": "Required for fill_in_blank: the sentence with ___ where the blank goes (e.g., 'My favorite way to recharge is ___')"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["origin_story", "creative_spark", "collaboration", "future_vision", "community_connection", "hidden_depths", "impact_legacy"]
                        },
                        "difficulty_level": {"type": "integer", "minimum": 1, "maximum": 3},
                        "purpose": {"type": "string"},
                        "follow_up_prompts": {"type": "array", "items": {"type": "string"}},
                        "potential_insights": {"type": "array", "items": {"type": "string"}},
                        "related_profile_fields": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["question_text", "question_type", "category", "purpose"]
                },
                "description": "The questions to include in this deck"
            }
        },
        "required": ["name", "description", "questions"]
    }
}


# Pattern discovery tools

async def save_pattern(db: AsyncSession, pattern_data: dict[str, Any]) -> dict[str, Any]:
    """
    Save or update a discovered pattern.

    If a pattern with the same name exists, it will be updated.
    Otherwise, a new pattern is created.

    Args:
        db: Database session.
        pattern_data: Pattern data including name, description, category, etc.

    Returns:
        dict with pattern id, name, and whether it was created or updated.
    """
    name = pattern_data.get("name")
    if not name:
        return {"error": "Pattern name is required"}

    # Check for existing pattern by name
    result = await db.execute(
        select(Pattern).where(Pattern.name == name)
    )
    pattern = result.scalar_one_or_none()

    # Convert category string to enum if needed
    category = pattern_data.get("category")
    if isinstance(category, str):
        try:
            category = PatternCategory(category)
        except ValueError:
            return {"error": f"Invalid category: {category}"}

    was_created = pattern is None

    if pattern:
        # Update existing pattern
        pattern.description = pattern_data.get("description", pattern.description)
        pattern.category = category or pattern.category
        pattern.member_count = pattern_data.get("member_count", pattern.member_count)
        pattern.related_member_ids = pattern_data.get("related_member_ids", pattern.related_member_ids)
        pattern.evidence = pattern_data.get("evidence", pattern.evidence)
        pattern.question_prompts = pattern_data.get("question_prompts", pattern.question_prompts)
        pattern.is_active = pattern_data.get("is_active", pattern.is_active)
    else:
        # Create new pattern
        pattern = Pattern(
            name=name,
            description=pattern_data.get("description", ""),
            category=category,
            member_count=pattern_data.get("member_count", 0),
            related_member_ids=pattern_data.get("related_member_ids", []),
            evidence=pattern_data.get("evidence"),
            question_prompts=pattern_data.get("question_prompts", []),
            is_active=pattern_data.get("is_active", True),
        )
        db.add(pattern)

    await db.commit()
    await db.refresh(pattern)

    return {
        "id": pattern.id,
        "name": pattern.name,
        "created": was_created,
        "updated": not was_created,
    }


async def get_active_patterns(db: AsyncSession) -> dict[str, Any]:
    """
    Retrieve all active patterns discovered in the community.

    Returns patterns with their descriptions, categories, member counts,
    evidence, and question prompts that can inform question generation.
    """
    result = await db.execute(
        select(Pattern).where(Pattern.is_active == True).order_by(Pattern.member_count.desc())
    )
    patterns = result.scalars().all()

    return {
        "total_patterns": len(patterns),
        "patterns": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "member_count": p.member_count,
                "related_member_ids": p.related_member_ids or [],
                "evidence": p.evidence or {},
                "question_prompts": p.question_prompts or [],
            }
            for p in patterns
        ],
    }


GET_ACTIVE_PATTERNS_TOOL = {
    "name": "get_active_patterns",
    "description": """Retrieve all active community patterns discovered by the pattern finder.

Each pattern includes:
- name: Short identifier (e.g., 'Creative Technologists')
- description: What this pattern reveals about the community
- category: One of skill_cluster, interest_theme, collaboration_opportunity, community_strength, cross_domain
- member_count: How many members exhibit this pattern
- related_member_ids: Which specific members relate to this pattern
- evidence: Supporting data like skill/interest frequencies
- question_prompts: 2-3 suggested questions to explore the pattern further

Use these patterns to:
1. Generate questions that explore discovered community themes
2. Create questions that could surface additional members who fit patterns
3. Design questions that deepen understanding of why these patterns exist
4. Craft questions that facilitate connections between pattern-related members""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


SAVE_PATTERN_TOOL = {
    "name": "save_pattern",
    "description": "Save a discovered pattern to the database. If a pattern with the same name exists, it will be updated.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short, unique pattern name (e.g., 'Tech + Arts Fusion')"
            },
            "description": {
                "type": "string",
                "description": "Detailed description of what this pattern reveals about the community"
            },
            "category": {
                "type": "string",
                "enum": ["skill_cluster", "interest_theme", "collaboration_opportunity", "community_strength", "cross_domain"],
                "description": "Category of pattern"
            },
            "member_count": {
                "type": "integer",
                "description": "Number of members who exhibit this pattern"
            },
            "related_member_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "IDs of members who exhibit this pattern"
            },
            "evidence": {
                "type": "object",
                "description": "Supporting data (e.g., skill names, frequencies, examples)"
            },
            "question_prompts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 questions that could explore this pattern further"
            }
        },
        "required": ["name", "description", "category", "member_count"]
    }
}
