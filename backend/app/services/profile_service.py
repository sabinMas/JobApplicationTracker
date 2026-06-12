"""
Profile merging logic for intelligent profile updates.

When extracting from a resume, we intelligently merge extracted data with
the existing profile to preserve manual entries while accepting new information.
"""

import logging
from typing import Optional
from ..models import Profile

logger = logging.getLogger(__name__)


def _is_empty_string(value: Optional[str]) -> bool:
    """Check if a string is None or empty/whitespace."""
    return value is None or (isinstance(value, str) and not value.strip())


def _merge_string_field(existing: Optional[str], extracted: Optional[str], field_name: str) -> tuple[Optional[str], bool]:
    """
    Merge a single string field.

    Strategy:
    - If existing is non-empty, preserve it (assume user manually entered)
    - If existing is empty/null and extracted has value, use extracted
    - If both empty/null, result is None
    - Return (merged_value, changed)
    """
    if not _is_empty_string(existing):
        # User has manually entered something, preserve it
        return existing, False

    if not _is_empty_string(extracted):
        # Extracted has value and existing is empty, use extracted
        return extracted, True

    # Both empty
    return None, False


def _merge_array_field(existing: list, extracted: list, field_name: str, dedup_key: str = "name") -> tuple[list, bool]:
    """
    Merge array field (skills, experience, education, certifications).

    Strategy:
    - Keep all existing items (maintain order and manual entries)
    - Add extracted items not already present (dedup by key)
    - Return (merged_list, changed)

    Args:
        existing: List of existing items (dicts or strings)
        extracted: List of extracted items (dicts or strings)
        field_name: Field name (skills, experience, etc.)
        dedup_key: Key to use for deduplication (name, title, school, etc.)
    """
    existing = existing or []
    extracted = extracted or []

    if not extracted:
        return existing, False

    merged = list(existing)  # Start with copy of existing
    changed = False

    for item in extracted:
        # Extract identifier based on field type
        if isinstance(item, dict):
            # For dicts (experience, education, certifications)
            if field_name == "skills":
                item_id = item
            elif field_name == "experience":
                item_id = (item.get("company", ""), item.get("title", ""))
            elif field_name == "education":
                item_id = (item.get("school", ""), item.get("degree", ""))
            elif field_name == "certifications":
                item_id = item.get("name", "")
            else:
                item_id = item
        # Check if already exists
        already_exists = False
        for existing_item in merged:
            if isinstance(existing_item, dict) and isinstance(item, dict):
                if field_name == "experience":
                    if (existing_item.get("company", "").lower() == item.get("company", "").lower() and
                        existing_item.get("title", "").lower() == item.get("title", "").lower()):
                        already_exists = True
                        break
                elif field_name == "education":
                    if (existing_item.get("school", "").lower() == item.get("school", "").lower() and
                        existing_item.get("degree", "").lower() == item.get("degree", "").lower()):
                        already_exists = True
                        break
                elif field_name == "certifications":
                    if existing_item.get("name", "").lower() == item.get("name", "").lower():
                        already_exists = True
                        break
            elif isinstance(existing_item, str) and isinstance(item, str):
                # String comparison (for skills)
                if existing_item.lower() == item.lower():
                    already_exists = True
                    break

        if not already_exists:
            merged.append(item)
            changed = True

    return merged, changed


async def merge_extracted_profile(existing_profile: Profile, extracted_data: dict) -> tuple[Profile, list[str]]:
    """
    Intelligently merge extracted resume data with existing profile.

    Strategy:
    - String fields: preserve manual entries, fill empty fields with extracted
    - Array fields: append extracted items, deduplicate
    - Returns: (merged_profile, list_of_changed_fields)

    Args:
        existing_profile: Profile object from DB (may be mostly empty on first extract)
        extracted_data: Dict from AI extraction (may be partial or empty)

    Returns:
        (merged_profile_object, list_of_field_names_that_changed)
    """
    if not extracted_data:
        logger.warning("No extracted data provided, returning unmodified profile")
        return existing_profile, []

    changed_fields = []

    # String fields
    for field in ["full_name", "email", "phone", "location", "summary", "linkedin_url", "github_url", "portfolio_url"]:
        existing_val = getattr(existing_profile, field, None)
        extracted_val = extracted_data.get(field)

        merged_val, changed = _merge_string_field(existing_val, extracted_val, field)
        if changed:
            setattr(existing_profile, field, merged_val)
            changed_fields.append(field)

    # Array fields with deduplication
    for field in ["skills", "experience", "education", "certifications"]:
        existing_val = getattr(existing_profile, field, None) or []
        extracted_val = extracted_data.get(field) or []

        merged_val, changed = _merge_array_field(existing_val, extracted_val, field)
        if changed:
            setattr(existing_profile, field, merged_val)
            changed_fields.append(field)

    logger.info(f"Profile merge complete: {len(changed_fields)} fields changed: {changed_fields}")
    return existing_profile, changed_fields
