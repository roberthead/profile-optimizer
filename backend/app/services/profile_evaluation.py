"""Profile evaluation service for calculating completeness scores."""

from typing import Dict
from app.models import Member, ProfileCompleteness
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime


class ProfileEvaluator:
    """Evaluates member profile completeness."""

    # Define which fields are required vs optional
    REQUIRED_FIELDS = {
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email",
    }

    OPTIONAL_FIELDS = {
        "profile_photo_url": "Profile Photo",
        "what_you_do": "What You Do",
        "where_location": "Location",
        "website": "Website",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_member(self, member_id: int) -> Dict:
        """
        Evaluate a member's profile completeness.

        Returns:
            Dict with completeness_score, missing_fields, optional_missing, last_calculated
        """
        # Get member
        result = await self.db.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()

        if not member:
            raise ValueError(f"Member with id {member_id} not found")

        missing_required = []
        missing_optional = []

        # Check required fields
        for field, label in self.REQUIRED_FIELDS.items():
            value = getattr(member, field, None)
            if not value or (isinstance(value, str) and value.strip() == ""):
                missing_required.append(label)

        # Check optional fields
        for field, label in self.OPTIONAL_FIELDS.items():
            value = getattr(member, field, None)
            if not value or (isinstance(value, str) and value.strip() == ""):
                missing_optional.append(label)

        # Calculate completeness score
        total_fields = len(self.REQUIRED_FIELDS) + len(self.OPTIONAL_FIELDS)
        filled_fields = total_fields - len(missing_required) - len(missing_optional)
        completeness_score = int((filled_fields / total_fields) * 100)

        # Store or update in database
        result = await self.db.execute(
            select(ProfileCompleteness).where(ProfileCompleteness.member_id == member_id)
        )
        profile_completeness = result.scalar_one_or_none()

        if profile_completeness:
            profile_completeness.completeness_score = completeness_score
            profile_completeness.missing_fields = {
                "required": missing_required,
                "optional": missing_optional
            }
            profile_completeness.last_calculated = datetime.utcnow()
        else:
            profile_completeness = ProfileCompleteness(
                member_id=member_id,
                completeness_score=completeness_score,
                missing_fields={
                    "required": missing_required,
                    "optional": missing_optional
                },
                last_calculated=datetime.utcnow()
            )
            self.db.add(profile_completeness)

        await self.db.commit()
        await self.db.refresh(profile_completeness)

        return {
            "completeness_score": completeness_score,
            "missing_fields": missing_required,
            "optional_missing": missing_optional,
            "last_calculated": profile_completeness.last_calculated.isoformat()
        }
