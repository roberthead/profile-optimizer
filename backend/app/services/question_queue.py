"""Pattern-driven question queue builder.

Pure algorithmic service — no LLM. Selects and sequences the best questions
for a given member based on pattern affinity, profile gaps, and difficulty.
"""

from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Member,
    Pattern,
    Question,
    QuestionResponse,
)


@dataclass
class ScoredQuestion:
    """A question with its computed score and selection metadata."""
    question_id: int
    question_text: str
    question_type: str
    category: str
    difficulty: int
    options: list[str]
    blank_prompt: Optional[str]
    score: float = 0.0
    reason: str = "fallback"
    reason_detail: str = ""
    related_patterns: list[dict] = field(default_factory=list)


class QuestionQueueBuilder:
    """Builds a prioritized queue of 10 questions for a member.

    Scoring factors (additive):
        Pattern Probe  — 10.0 * affinity  (question probes pattern member is NOT in)
        Pattern Deepen —  5.0 * ratio      (question deepens pattern member IS in)
        Profile Gap    —  4.0 * ratio      (question targets empty profile fields)
        Fallback       —  1.0              (has profile field targets but no pattern link)
        Minimum        —  0.1              (every question)

    Sequencing (top 10 after scoring):
        Positions 1-3:  Easy  (difficulty 1), prefer profile_gap
        Positions 4-7:  Medium (difficulty 2), prefer pattern_probe
        Positions 8-10: Deep  (difficulty 3), prefer pattern_deepen
    """

    AFFINITY_THRESHOLD = 0.3

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_queue(self, member_id: int) -> dict:
        """Build a scored + sequenced question queue for a member.

        Returns a dict with member_id, member_name, queue (list of question dicts),
        and scoring_summary.
        """
        # --- a) Load data ---
        member = await self._load_member(member_id)
        if member is None:
            return None

        patterns = await self._load_active_patterns()
        answered_ids = await self._load_answered_question_ids(member_id)
        questions = await self._load_available_questions(answered_ids)

        if not questions:
            member_name = f"{member.first_name or ''} {member.last_name or ''}".strip() or member.email
            return {
                "member_id": member_id,
                "member_name": member_name,
                "queue": [],
                "scoring_summary": self._build_scoring_summary(
                    questions_available=0,
                    answered_count=len(answered_ids),
                    member_pattern_ids=[],
                    high_affinity_patterns=[],
                    profile_gaps=[],
                ),
            }

        # --- b) Compute pattern affinity ---
        member_skills = set(s.lower() for s in (member.skills or []))
        member_interests = set(i.lower() for i in (member.interests or []))

        member_pattern_ids: list[int] = []
        pattern_affinities: dict[int, float] = {}
        pattern_lookup: dict[int, Pattern] = {}

        for pattern in patterns:
            pattern_lookup[pattern.id] = pattern
            related_ids = pattern.related_member_ids or []

            if member_id in related_ids:
                member_pattern_ids.append(pattern.id)
                continue

            # Compute affinity for patterns the member is NOT in
            evidence = pattern.evidence or {}
            evidence_skills = set(
                s.lower() for s in (evidence.get("skills") or evidence.get("skill_names") or [])
            )
            evidence_interests = set(
                i.lower() for i in (evidence.get("interests") or evidence.get("interest_names") or [])
            )

            if not evidence_skills and not evidence_interests:
                continue

            skill_overlap = (
                len(member_skills & evidence_skills) / len(evidence_skills)
                if evidence_skills else 0.0
            )
            interest_overlap = (
                len(member_interests & evidence_interests) / len(evidence_interests)
                if evidence_interests else 0.0
            )
            affinity = 0.6 * skill_overlap + 0.4 * interest_overlap

            if affinity >= self.AFFINITY_THRESHOLD:
                pattern_affinities[pattern.id] = affinity

        # --- Profile gap detection ---
        profile_gaps = self._detect_profile_gaps(member)
        gap_fields = set(g["field"] for g in profile_gaps)

        # --- c) Score each question ---
        scored: list[ScoredQuestion] = []

        for q in questions:
            sq = ScoredQuestion(
                question_id=q.id,
                question_text=q.question_text,
                question_type=q.question_type.value,
                category=q.category.value,
                difficulty=q.difficulty_level,
                options=q.options or [],
                blank_prompt=q.blank_prompt,
                score=0.1,  # minimum
                reason="minimum",
                reason_detail="Base score",
            )

            q_pattern_ids = set(q.related_pattern_ids or [])
            q_profile_fields = set(q.related_profile_fields or [])
            reasons: list[str] = []

            # Pattern Probe: question probes pattern member is NOT in, but has affinity
            for pid in q_pattern_ids:
                if pid in pattern_affinities:
                    affinity = pattern_affinities[pid]
                    sq.score += 10.0 * affinity
                    p = pattern_lookup.get(pid)
                    pattern_name = p.name if p else f"Pattern {pid}"
                    reasons.append(f"Probes '{pattern_name}' (affinity {affinity:.2f})")
                    sq.related_patterns.append({
                        "id": pid,
                        "name": pattern_name,
                        "relationship": "probe",
                        "affinity": round(affinity, 2),
                    })

            # Pattern Deepen: question deepens pattern member IS in
            deepened_ids = q_pattern_ids & set(member_pattern_ids)
            if deepened_ids:
                ratio = len(deepened_ids) / max(len(member_pattern_ids), 1)
                sq.score += 5.0 * ratio
                for pid in deepened_ids:
                    p = pattern_lookup.get(pid)
                    pattern_name = p.name if p else f"Pattern {pid}"
                    reasons.append(f"Deepens '{pattern_name}'")
                    sq.related_patterns.append({
                        "id": pid,
                        "name": pattern_name,
                        "relationship": "deepen",
                    })

            # Profile Gap: question targets empty fields
            matching_gaps = q_profile_fields & gap_fields
            if matching_gaps:
                ratio = len(matching_gaps) / max(len(q_profile_fields), 1)
                sq.score += 4.0 * ratio
                reasons.append(f"Fills gaps: {', '.join(sorted(matching_gaps))}")

            # Fallback: has profile field targets but no pattern link
            if q_profile_fields and not q_pattern_ids:
                sq.score += 1.0
                if not reasons:
                    reasons.append("Targets profile fields")

            # Determine primary reason
            if any("Probes" in r for r in reasons):
                sq.reason = "pattern_probe"
            elif any("Deepens" in r for r in reasons):
                sq.reason = "pattern_deepen"
            elif any("Fills gaps" in r for r in reasons):
                sq.reason = "profile_gap"
            elif any("Targets" in r for r in reasons):
                sq.reason = "fallback"

            sq.reason_detail = "; ".join(reasons) if reasons else "Base score"

            scored.append(sq)

        # --- d) Select top 10, then sequence ---
        scored.sort(key=lambda s: s.score, reverse=True)
        top = scored[:10]
        sequenced = self._sequence(top)

        member_name = f"{member.first_name or ''} {member.last_name or ''}".strip() or member.email
        high_affinity = [
            {"id": pid, "name": pattern_lookup[pid].name, "affinity": round(aff, 2)}
            for pid, aff in sorted(pattern_affinities.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "member_id": member_id,
            "member_name": member_name,
            "queue": [
                {
                    "position": i + 1,
                    "question_id": sq.question_id,
                    "question_text": sq.question_text,
                    "type": sq.question_type,
                    "category": sq.category,
                    "difficulty": sq.difficulty,
                    "options": sq.options,
                    "blank_prompt": sq.blank_prompt,
                    "score": round(sq.score, 2),
                    "reason": sq.reason,
                    "reason_detail": sq.reason_detail,
                    "related_patterns": sq.related_patterns,
                }
                for i, sq in enumerate(sequenced)
            ],
            "scoring_summary": self._build_scoring_summary(
                questions_available=len(questions),
                answered_count=len(answered_ids),
                member_pattern_ids=member_pattern_ids,
                high_affinity_patterns=high_affinity,
                profile_gaps=profile_gaps,
            ),
        }

    # --- Data loading helpers ---

    async def _load_member(self, member_id: int) -> Optional[Member]:
        result = await self.db.execute(
            select(Member).where(Member.id == member_id)
        )
        return result.scalar_one_or_none()

    async def _load_active_patterns(self) -> list[Pattern]:
        result = await self.db.execute(
            select(Pattern).where(Pattern.is_active == True)
        )
        return list(result.scalars().all())

    async def _load_answered_question_ids(self, member_id: int) -> set[int]:
        result = await self.db.execute(
            select(QuestionResponse.question_id).where(
                QuestionResponse.member_id == member_id
            )
        )
        return set(result.scalars().all())

    async def _load_available_questions(self, answered_ids: set[int]) -> list[Question]:
        query = select(Question).where(Question.is_active == True)
        if answered_ids:
            query = query.where(Question.id.notin_(answered_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # --- Profile gap detection ---

    @staticmethod
    def _detect_profile_gaps(member: Member) -> list[dict]:
        """Check which profile fields are empty or insufficient."""
        gaps = []
        if not member.bio or len(member.bio) < 50:
            gaps.append({"field": "bio", "label": "Bio (>= 50 chars)"})
        if not member.role:
            gaps.append({"field": "role", "label": "Role"})
        if not member.company:
            gaps.append({"field": "company", "label": "Company"})
        if not member.location:
            gaps.append({"field": "location", "label": "Location"})
        if not member.website:
            gaps.append({"field": "website", "label": "Website"})
        if not member.skills or len(member.skills) < 3:
            gaps.append({"field": "skills", "label": "Skills (>= 3)"})
        if not member.interests or len(member.interests) < 1:
            gaps.append({"field": "interests", "label": "Interests (>= 1)"})
        if not member.prompt_responses or len(member.prompt_responses) < 1:
            gaps.append({"field": "prompt_responses", "label": "Prompt responses (>= 1)"})
        return gaps

    # --- Sequencing ---

    @staticmethod
    def _sequence(questions: list[ScoredQuestion]) -> list[ScoredQuestion]:
        """Sequence the top questions into warm-up / explore / deep buckets.

        Positions 1-3:  prefer difficulty 1 + profile_gap reason
        Positions 4-7:  prefer difficulty 2 + pattern_probe reason
        Positions 8-10: prefer difficulty 3 + pattern_deepen reason

        Falls back gracefully when ideal candidates aren't available.
        """
        remaining = list(questions)
        result: list[ScoredQuestion] = []

        def pick_best(pool: list[ScoredQuestion], preferred_difficulty: int, preferred_reason: str) -> ScoredQuestion:
            """Pick the best match from pool, preferring difficulty and reason."""
            if not pool:
                raise ValueError("Empty pool")

            def sort_key(sq: ScoredQuestion) -> tuple:
                diff_match = 1 if sq.difficulty == preferred_difficulty else 0
                reason_match = 1 if sq.reason == preferred_reason else 0
                return (diff_match + reason_match, sq.score)

            pool.sort(key=sort_key, reverse=True)
            return pool[0]

        # Positions 1-3: Easy, prefer profile_gap
        for _ in range(min(3, len(remaining))):
            best = pick_best(remaining, 1, "profile_gap")
            result.append(best)
            remaining.remove(best)

        # Positions 4-7: Medium, prefer pattern_probe
        for _ in range(min(4, len(remaining))):
            best = pick_best(remaining, 2, "pattern_probe")
            result.append(best)
            remaining.remove(best)

        # Positions 8-10: Deep, prefer pattern_deepen
        for _ in range(min(3, len(remaining))):
            best = pick_best(remaining, 3, "pattern_deepen")
            result.append(best)
            remaining.remove(best)

        return result

    # --- Summary ---

    @staticmethod
    def _build_scoring_summary(
        questions_available: int,
        answered_count: int,
        member_pattern_ids: list[int],
        high_affinity_patterns: list[dict],
        profile_gaps: list[dict],
    ) -> dict:
        return {
            "total_available": questions_available,
            "already_answered": answered_count,
            "pattern_memberships": len(member_pattern_ids),
            "high_affinity_patterns": high_affinity_patterns,
            "profile_gaps": profile_gaps,
        }
