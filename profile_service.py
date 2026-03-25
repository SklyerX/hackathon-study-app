from typing import Optional
from uuid import UUID
from supabase import Client

from study_app.database import get_supabase
from study_app.profile import (
    CreateProfileRequest,
    UpdateProfileRequest,
    LearnerProfileResponse,
    ProfileType,
)


class ProfileService:

    def __init__(self):
        self.db: Client = get_supabase()

    def ensure_user(self, user_id: str, email: str = "") -> None:
        """
        Insert user row if it doesn't exist. Safe to call multiple times.
        In production this is handled by a Supabase Auth trigger —
        keeping it here for dev convenience.
        """
        self.db.table("users").upsert(
            {"id": user_id, "email": email or f"{user_id}@placeholder.dev"},
            on_conflict="id",
        ).execute()

    def create_profile(
        self, user_id: str, req: CreateProfileRequest
    ) -> LearnerProfileResponse:
        """
        Create a learner profile for a user.
        Raises an error if the user already has a profile (use update instead).
        """
        self.ensure_user(user_id)

        data = {
            "user_id": user_id,
            "profile_type": req.profile_type.value,
            "native_language": req.native_language,
            "english_level": req.english_level,
            "chunk_duration_mins": req.chunk_duration_mins,
            "gamification_on": req.gamification_on,
            "preferred_voice": req.preferred_voice,
            "font_size_pref": req.font_size_pref,
        }

        result = self.db.table("learner_profiles").insert(data).execute()
        return LearnerProfileResponse(**result.data[0])

    def update_profile(
        self, user_id: str, req: UpdateProfileRequest
    ) -> LearnerProfileResponse:
        """Partial update — only changed fields are written."""
        updates = req.model_dump(exclude_none=True)
        if "profile_type" in updates:
            updates["profile_type"] = updates["profile_type"].value

        result = (
            self.db.table("learner_profiles")
            .update(updates)
            .eq("user_id", user_id)
            .execute()
        )
        return LearnerProfileResponse(**result.data[0])

    def upsert_profile(
        self, user_id: str, req: CreateProfileRequest
    ) -> LearnerProfileResponse:
        """
        Convenience method: create if not exists, update if exists.
        Ideal for onboarding flows where the user may re-submit their profile.
        """
        existing = self.get_profile(user_id)
        if existing:
            update_req = UpdateProfileRequest(**req.model_dump())
            return self.update_profile(user_id, update_req)
        return self.create_profile(user_id, req)
