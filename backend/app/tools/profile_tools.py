"""Tools for profile evaluation that can be used by LLM agents."""

from typing import Any
from app.models import Member


def get_field_completeness(member: Member) -> dict[str, Any]:
    """
    Check which profile fields are filled vs empty.
    Returns a structured report of field completion status.
    """
    # Define all evaluatable fields with their display names and importance
    FIELDS = {
        # Identity fields (required)
        "first_name": {"label": "First Name", "category": "identity", "required": True},
        "last_name": {"label": "Last Name", "category": "identity", "required": True},
        "email": {"label": "Email", "category": "identity", "required": True},

        # Core profile fields
        "bio": {"label": "Bio", "category": "core", "required": False},
        "role": {"label": "Role/Title", "category": "core", "required": False},
        "location": {"label": "Location", "category": "core", "required": False},

        # Professional fields
        "company": {"label": "Company", "category": "professional", "required": False},
        "website": {"label": "Website", "category": "professional", "required": False},

        # Visual
        "profile_photo_url": {"label": "Profile Photo", "category": "visual", "required": False},
    }

    # Array fields need special handling
    ARRAY_FIELDS = {
        "skills": {"label": "Skills", "category": "discoverability", "required": False},
        "interests": {"label": "Interests", "category": "discoverability", "required": False},
        "urls": {"label": "URLs/Links", "category": "professional", "required": False},
        "prompt_responses": {"label": "Prompt Responses", "category": "rich_content", "required": False},
        "roles": {"label": "Community Roles", "category": "community", "required": False},
        "all_traits": {"label": "Traits", "category": "discoverability", "required": False},
    }

    filled_fields = []
    empty_fields = []
    field_details = {}

    # Check scalar fields
    for field_name, field_info in FIELDS.items():
        value = getattr(member, field_name, None)
        is_filled = bool(value and (not isinstance(value, str) or value.strip()))

        field_details[field_name] = {
            **field_info,
            "filled": is_filled,
            "value": value if is_filled else None,
        }

        if is_filled:
            filled_fields.append(field_info["label"])
        else:
            empty_fields.append(field_info["label"])

    # Check array fields
    for field_name, field_info in ARRAY_FIELDS.items():
        value = getattr(member, field_name, None) or []
        count = len(value) if value else 0
        is_filled = count > 0

        field_details[field_name] = {
            **field_info,
            "filled": is_filled,
            "count": count,
            "values": value if is_filled else [],
        }

        if is_filled:
            filled_fields.append(f"{field_info['label']} ({count})")
        else:
            empty_fields.append(field_info["label"])

    # Calculate simple percentage
    total_fields = len(FIELDS) + len(ARRAY_FIELDS)
    filled_count = len([f for f in field_details.values() if f["filled"]])
    basic_percentage = int((filled_count / total_fields) * 100)

    return {
        "member_id": member.id,
        "member_name": f"{member.first_name or ''} {member.last_name or ''}".strip() or member.email,
        "basic_completeness_percentage": basic_percentage,
        "total_fields": total_fields,
        "filled_count": filled_count,
        "empty_count": total_fields - filled_count,
        "filled_fields": filled_fields,
        "empty_fields": empty_fields,
        "field_details": field_details,
    }


# Tool definition for Claude API
FIELD_COMPLETENESS_TOOL = {
    "name": "get_field_completeness",
    "description": "Check which profile fields are filled vs empty for a member. Returns a detailed report of all fields, their values, and completion status. Use this to understand the current state of a member's profile before making an assessment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The ID of the member whose profile to check"
            }
        },
        "required": ["member_id"]
    }
}
