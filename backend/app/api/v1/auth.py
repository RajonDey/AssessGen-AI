"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service, get_current_user
from app.api.errors import InvalidCredentialsProblem
from app.domain.entities.user import AuthenticatedUser
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse
from app.services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        return await auth_service.login(body)
    except InvalidCredentialsError as exc:
        raise InvalidCredentialsProblem from exc


@router.get("/me", response_model=UserMeResponse)
async def me(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserMeResponse:
    return AuthService.to_me_response(user)
