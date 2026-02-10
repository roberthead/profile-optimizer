#!/usr/bin/env python3
"""
Seed script to populate the members table from the White Rabbit API.

Usage:
    cd backend
    source venv/bin/activate

    # Fetch from API
    python -m app.scripts.seed_members [--clear]

    # Dry run (preview without committing)
    python -m app.scripts.seed_members --dry-run

Options:
    --clear     Clear existing members before seeding
    --dry-run   Preview changes without committing to database
"""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import Member, SocialLink, ConversationHistory, ProfileCompleteness
from app.utils import normalize_string, normalize_list, parse_datetime


async def seed_members(
    session: AsyncSession,
    data: list[dict],
    clear_existing: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Seed members from API data.

    Args:
        session: Database session.
        data: List of member data dictionaries.
        clear_existing: If True, clear all existing members first.
        dry_run: If True, preview changes without committing.

    Returns:
        Tuple of (created_count, updated_count, skipped_count)
    """
    created = 0
    updated = 0
    skipped = 0

    if dry_run:
        print("[DRY RUN] No changes will be committed to the database.")

    if clear_existing:
        if dry_run:
            print("[DRY RUN] Would clear existing members and related data.")
        else:
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
            # Handle both API format (id, camelCase) and export format (profile_id, snake_case)
            profile_id = (
                record.get("profile_id") or record.get("profileId") or record.get("id")
            )

            # API doesn't return email/clerk_user_id for privacy - generate placeholders
            clerk_user_id = (
                record.get("clerk_user_id")
                or record.get("clerkUserId")
                or f"api_sync_{profile_id}"
            )
            email = (
                record.get("clerk_email")
                or record.get("clerkEmail")
                or record.get("email")
                or f"{profile_id}@api-sync.local"
            )

            if not profile_id:
                print(f"Skipping record with missing profile_id: {record}")
                skipped += 1
                continue

            # Skip duplicates by email within the source data
            if email in seen_emails:
                print(f"Skipping duplicate email in source: {email}")
                skipped += 1
                continue
            seen_emails.add(email)

            # Check if member already exists (by profile_id)
            existing = await session.execute(
                select(Member).where(Member.profile_id == profile_id)
            )
            existing_member = existing.scalar_one_or_none()

            # Extract skills and interests from traits array (API format)
            traits = record.get("traits", [])
            skills_from_traits = [
                t.get("name") for t in traits if t.get("relationshipType") == "SKILL"
            ]
            interests_from_traits = [
                t.get("name") for t in traits if t.get("relationshipType") == "INTEREST"
            ]
            all_trait_names = [t.get("name") for t in traits]

            # Extract prompt response texts (API format)
            prompt_responses_api = record.get("promptResponses", [])
            prompt_response_texts = [
                f"{pr.get('promptText', '')}: {pr.get('responseText', '')}"
                for pr in prompt_responses_api
                if pr.get("responseText")
            ]

            # Map membershipTier to membership_status
            membership_tier = record.get("membershipTier", "")
            membership_status_map = {
                "Creator": "active_create",
                "Fellow": "active_fellow",
                "Team": "active_team_member",
                "Free": "free",
            }
            membership_status = membership_status_map.get(
                membership_tier,
                record.get("membership_status")
                or record.get("membershipStatus")
                or "free",
            )

            member_data = {
                "profile_id": profile_id,
                "clerk_user_id": clerk_user_id,
                "email": email,
                "first_name": normalize_string(
                    record.get("first_name") or record.get("firstName")
                ),
                "last_name": normalize_string(
                    record.get("last_name") or record.get("lastName")
                ),
                "profile_photo_url": normalize_string(
                    record.get("avatar") or record.get("profile_photo_url")
                ),
                "bio": normalize_string(record.get("bio")),
                "company": normalize_string(record.get("company")),
                "role": normalize_string(record.get("role")),
                "website": normalize_string(record.get("website")),
                "location": normalize_string(record.get("location")),
                "membership_status": membership_status,
                "is_public": record.get("is_public")
                if record.get("is_public") is not None
                else record.get("isPublic", True),
                "urls": normalize_list(record.get("urls")),
                "roles": normalize_list(record.get("roles")),
                "prompt_responses": normalize_list(record.get("prompt_responses"))
                or prompt_response_texts,
                "skills": normalize_list(record.get("skills")) or skills_from_traits,
                "interests": normalize_list(record.get("interests"))
                or interests_from_traits,
                "all_traits": normalize_list(
                    record.get("all_traits") or record.get("allTraits")
                )
                or all_trait_names,
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
                created_at_val = record.get("created_at") or record.get("createdAt")
                if created_at_val:
                    parsed_created = parse_datetime(created_at_val)
                    if parsed_created:
                        member.created_at = parsed_created

                session.add(member)
                created += 1

            # Flush periodically to catch errors early (skip in dry run)
            if not dry_run and (created + updated) % 50 == 0:
                await session.flush()

        except Exception as e:
            if not dry_run:
                await session.rollback()
            print(f"Error processing record {record.get('profile_id', 'unknown')}: {e}")
            skipped += 1
            continue

    if dry_run:
        await session.rollback()
        print("[DRY RUN] Changes rolled back.")
    else:
        await session.commit()

    return created, updated, skipped


async def fetch_from_api() -> list[dict]:
    """
    Fetch member data from White Rabbit API.

    Returns:
        List of member data dictionaries.

    Raises:
        SystemExit: If API fetch fails.
    """
    from app.services import WhiteRabbitClient, WhiteRabbitAPIError

    try:
        client = WhiteRabbitClient()
        print(f"Fetching members from: {client.api_url}")
        data = await client.fetch_members()
        return data
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure WHITE_RABBIT_API_KEY is set in your environment.")
        sys.exit(1)
    except WhiteRabbitAPIError as e:
        print(f"API error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(description="Seed members from White Rabbit API")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing members before seeding",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Preview changes without committing to database",
    )
    args = parser.parse_args()

    data = await fetch_from_api()
    print(f"Found {len(data)} records to process")

    async with AsyncSessionLocal() as session:
        created, updated, skipped = await seed_members(
            session,
            data,
            clear_existing=args.clear,
            dry_run=args.dry_run,
        )

    print("\nSeeding complete:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
