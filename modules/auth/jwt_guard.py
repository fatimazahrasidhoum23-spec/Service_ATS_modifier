"""
modules/auth/jwt_guard.py
─────────────────────────
Guard JWT pour FastAPI.
Valide le token Bearer émis par AuthService (HMAC-SHA256).

Utilisation dans un endpoint :
    @app.get("/api/ats/score")
    async def score(current_user: dict = Depends(require_auth)):
        ...

Pour restreindre à un rôle précis :
    @app.post("/api/ats/feedback")
    async def feedback(current_user: dict = Depends(require_role("RH"))):
        ...

Si le token est expiré, le client doit appeler POST /api/auth/refresh-token
sur AuthService pour obtenir un nouveau access token.
"""

import os
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("ats.auth")

# ── Paramètres JWT (identiques à AuthService) ─────────────────────────────────
# Le secret vient uniquement de l'environnement (docker-compose ou .env), jamais du code
JWT_SECRET    = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("Variable d'environnement JWT_SECRET manquante (voir .env.example)")
JWT_ALGORITHM = "HS256"

# HTTPBearer extrait automatiquement le header Authorization: Bearer <token>
_bearer_scheme = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    """
    Décode et valide le token JWT.
    Lève HTTPException 401 si invalide ou expiré.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},   # AuthService n'encode pas l'audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré. Appelez POST /api/auth/refresh-token pour en obtenir un nouveau.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning("Token JWT invalide : %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """
    Dependency FastAPI — vérifie que le token est présent et valide.
    Retourne le payload JWT (userId, email, role).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant. Ajoutez Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    logger.debug(
        "Requête authentifiée — userId=%s role=%s",
        payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"),
        payload.get("http://schemas.microsoft.com/ws/2008/06/identity/claims/role"),
    )
    return payload


def require_role(required_role: str):
    """
    Dependency factory — vérifie en plus que l'utilisateur a le bon rôle.

    Exemple : Depends(require_role("RH"))
    """
    def _check(payload: dict = Depends(require_auth)) -> dict:
        # .NET encode les claims avec leur URI complet
        role_claim = payload.get(
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/role", ""
        )
        if role_claim != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle '{required_role}' requis. Vous avez : '{role_claim}'.",
            )
        return payload
    return _check
