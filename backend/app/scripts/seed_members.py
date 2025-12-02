#!/usr/bin/env python3
"""
Seed script to populate the members table from JSON export data.

Usage:
    cd backend
    source venv/bin/activate
    python -m app.scripts.seed_members [--file path/to/data.json] [--clear]

Options:
    --file      Path to the JSON file (default: data/member-data-export-*.json)
    --clear     Clear existing members before seeding
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import Member, SocialLink, ConversationHistory, ProfileCompleteness


def parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
    """Parse datetime string from JSON export."""
    if not dt_string:
        return None
    try:
        # Handle format: "2025-11-27 06:08:44.635426"
        return datetime.fromisoformat(dt_string.replace(" ", "T"))
    except ValueError:
        return None


def normalize_string(value: Optional[str]) -> Optional[str]:
    """Convert empty strings to None for cleaner data."""
    if value is None or value.strip() == "":
        return None
    return value.strip()


def normalize_list(value: Optional[list]) -> list:
    """Ensure list is not None and filter empty strings."""
    if not value:
        return []
    return [item for item in value if item and str(item).strip()]


async def seed_members(
    session: AsyncSession,
    data: list[dict],
    clear_existing: bool = False
) -> tuple[int, int, int]:
    """
    Seed members from JSON data.

    Returns:
        Tuple of (created_count, updated_count, skipped_count)
    """
    created = 0
    updated = 0
    skipped = 0

    if clear_existing:
        # Clear related tables first (foreign key constraints)
        await session.execute(delete(ProfileCompleteness))
        await session.execute(delete(ConversationHistory))
        await session.execute(delete(SocialLink))
        await session.execute(delete(Member))
        await session.commit()
        print("Cleared existing members and related data.")

    # Track seen emails to handle duplicates in source data
    seen_emails: set[str] = set()

    for record in data:
        try:
            profile_id = UUID(record["profile_id"])
            clerk_user_id = record["clerk_user_id"]
            email = record["clerk_email"]

            # Skip duplicates by email within the source data
            if email in seen_emails:
                print(f"Skipping duplicate email in source: {email}")
                skipped += 1
                continue
            seen_emails.add(email)

            # Check if member already exists (by profile_id, clerk_user_id, or email)
            existing = await session.execute(
                select(Member).where(
                    (Member.profile_id == profile_id) |
                    (Member.clerk_user_id == clerk_user_id) |
                    (Member.email == email)
                )
            )
            existing_member = existing.scalar_one_or_none()

            member_data = {
                "profile_id": profile_id,
                "clerk_user_id": clerk_user_id,
                "email": email,
                "first_name": normalize_string(record.get("first_name")),
                "last_name": normalize_string(record.get("last_name")),
                "bio": normalize_string(record.get("bio")),
                "company": normalize_string(record.get("company")),
                "role": normalize_string(record.get("role")),
                "website": normalize_string(record.get("website")),
                "location": normalize_string(record.get("location")),
                "membership_status": record.get("membership_status", "free"),
                "is_public": record.get("is_public", True),
                "urls": normalize_list(record.get("urls")),
                "roles": normalize_list(record.get("roles")),
                "prompt_responses": normalize_list(record.get("prompt_responses")),
                "skills": normalize_list(record.get("skills")),
                "interests": normalize_list(record.get("interests")),
                "all_traits": normalize_list(record.get("all_traits")),
            }

            if existing_member:
                # Update existing member
                for key, value in member_data.items():
                    setattr(existing_member, key, value)
                updated += 1
            else:
                # Create new member
                member = Member(**member_data)

                # Handle created_at/updated_at from source if available
                if record.get("created_at"):
                    parsed_created = parse_datetime(record["created_at"])
                    if parsed_created:
                        member.created_at = parsed_created

                session.add(member)
                created += 1

            # Flush periodically to catch errors early
            if (created + updated) % 50 == 0:
                await session.flush()

        except Exception as e:
            await session.rollback()
            print(f"Error processing record {record.get('profile_id', 'unknown')}: {e}")
            skipped += 1
            # Re-add seen_emails for already-processed records
            continue

    await session.commit()
    return created, updated, skipped


async def main():
    parser = argparse.ArgumentParser(description="Seed members from JSON export")
    parser.add_argument(
        "--file",
        type=str,
        help="Path to JSON file (default: latest in data/)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing members before seeding",
    )
    args = parser.parse_args()

    # Find the JSON file
    if args.file:
        json_path = Path(args.file)
    else:
        # Find the most recent export file in data/seeds/
        data_dir = Path(__file__).parent.parent.parent / "data" / "seeds"
        json_files = sorted(glob(str(data_dir / "member-data-export-*.json")))
        if not json_files:
            print("No member data export files found in data/seeds/ directory")
            sys.exit(1)
        json_path = Path(json_files[-1])  # Most recent by filename

    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    print(f"Loading data from: {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    print(f"Found {len(data)} records to process")

    async with AsyncSessionLocal() as session:
        created, updated, skipped = await seed_members(
            session, data, clear_existing=args.clear
        )

    print(f"\nSeeding complete:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
