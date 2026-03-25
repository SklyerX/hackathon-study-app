from fastapi import APIRouter, HTTPException, Depends

from study_app.profile import (
    CreateProfileRequest,
    UpdateProfileRequest,
    LearnerProfileResponse,
)
from study_app.profile_service import ProfileService

router = APIRouter(prefix="/api/profile", tags=["Learner Profile"])


def get_profile_service() -> ProfileService:
    return ProfileService()


@router.post("/{user_id}", response_model=LearnerProfileResponse, status_code=201)
def create_profile(
    user_id: str,
    req: CreateProfileRequest,
    service: ProfileService = Depends(get_profile_service),
):
    """Create a learner profile. Fails if one already exists — use /upsert instead."""
    try:
        return service.create_profile(user_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=LearnerProfileResponse)
def get_profile(
    user_id: str,
    service: ProfileService = Depends(get_profile_service),
):
    profile = service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile


@router.patch("/{user_id}", response_model=LearnerProfileResponse)
def update_profile(
    user_id: str,
    req: UpdateProfileRequest,
    service: ProfileService = Depends(get_profile_service),
):
    try:
        return service.update_profile(user_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}/upsert", response_model=LearnerProfileResponse)
def upsert_profile(
    user_id: str,
    req: CreateProfileRequest,
    service: ProfileService = Depends(get_profile_service),
):
    """Onboarding endpoint — creates profile if new, updates if returning user."""
    try:
        return service.upsert_profile(user_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
