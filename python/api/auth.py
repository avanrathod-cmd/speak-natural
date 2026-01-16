"""
Supabase authentication middleware and utilities.

Handles JWT token verification from Supabase frontend authentication.
Supports ES256 (Elliptic Curve) tokens using JWKS.
"""

import os
import jwt
import requests
from typing import Optional, Dict
from fastapi import HTTPException, Header, Depends
from datetime import datetime
from jwt import PyJWKClient
from functools import lru_cache


class SupabaseAuth:
    """Supabase authentication handler for backend verification."""

    def __init__(self):
        """Initialize Supabase auth with JWKS client."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')

        if not self.supabase_url:
            print("⚠️  Warning: SUPABASE_URL not set. Authentication will not work.")
            self.jwks_client = None
        else:
            # Initialize JWKS client to fetch public keys from Supabase
            jwks_url = f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
            self.jwks_client = PyJWKClient(jwks_url)
            print(f"✅ Supabase auth initialized with JWKS from {jwks_url}")

    def verify_token(self, token: str) -> dict:
        """
        Verify JWT token from Supabase frontend.

        Supports both ES256 (Elliptic Curve) and HS256 tokens.
        Uses JWKS (JSON Web Key Set) to fetch public keys for verification.

        Args:
            token: JWT token from Authorization header

        Returns:
            Decoded token payload with user info

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not self.jwks_client:
            raise HTTPException(
                status_code=500,
                detail="Server authentication not configured (missing SUPABASE_URL)"
            )

        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode JWT token with public key
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256", "HS256"],  # Support multiple algorithms
                audience="authenticated",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True
                }
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )

    def get_user_id(self, payload: dict) -> str:
        """
        Extract user ID from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            User ID (UUID from Supabase)
        """
        user_id = payload.get('sub')
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID"
            )
        return user_id

    def get_user_email(self, payload: dict) -> Optional[str]:
        """
        Extract user email from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            User email if available
        """
        return payload.get('email')

    def get_user_metadata(self, payload: dict) -> dict:
        """
        Extract user metadata from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            User metadata dict
        """
        return {
            "user_id": payload.get('sub'),
            "email": payload.get('email'),
            "role": payload.get('role'),
            "app_metadata": payload.get('app_metadata', {}),
            "user_metadata": payload.get('user_metadata', {})
        }


# Global auth instance
supabase_auth = SupabaseAuth()


# Dependency for protected routes
async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            user_id = user["user_id"]
            ...

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User metadata dict

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )

    token = parts[1]

    # Verify token and extract user info
    payload = supabase_auth.verify_token(token)
    user_metadata = supabase_auth.get_user_metadata(payload)

    return user_metadata


# Optional auth dependency (doesn't require token)
async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    FastAPI dependency for optional authentication.

    Returns user info if token is provided and valid, otherwise None.

    Usage:
        @app.get("/public-or-protected")
        async def route(user: Optional[dict] = Depends(get_current_user_optional)):
            if user:
                # Authenticated behavior
                user_id = user["user_id"]
            else:
                # Public behavior
                pass

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User metadata dict if authenticated, None otherwise
    """
    if not authorization:
        return None

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]
        payload = supabase_auth.verify_token(token)
        return supabase_auth.get_user_metadata(payload)

    except HTTPException:
        return None
    except Exception:
        return None
