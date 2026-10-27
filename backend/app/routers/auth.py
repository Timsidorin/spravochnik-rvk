import asyncio

from fastapi import APIRouter, HTTPException, status
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPSocketOpenError,
    LDAPException,
)

from ..config import settings
from ..schemas import LoginRequest, TokenResponse
from ..auth import create_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _bind_check(username: str, password: str) -> None:
    """Синхронный bind к AD. Выполняется в thread pool."""
    server = Server(settings.ad_server, get_info=ALL)
    conn = Connection(
        server,
        user=username,
        password=password,
        auto_bind=True,
    )
    try:
        conn.unbind()
    except Exception:
        pass


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    try:
        await asyncio.to_thread(_bind_check, req.username, req.password)
    except LDAPBindError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    except LDAPSocketOpenError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Сервер AD недоступен: {e}",
        )
    except LDAPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка LDAP: {e}",
        )

    is_admin = req.username.strip().lower() in settings.admin_logins
    token = create_token(req.username, is_admin)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=req.username,
        is_admin=is_admin,
    )