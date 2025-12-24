import os
import bcrypt
import httpx
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from pydantic import BaseModel

from .config import global_args

# use the .env that is inside the current folder
# allows to use different .env file for each lightrag instance
# the OS environment variables take precedence over the .env file
load_dotenv(dotenv_path=".env", override=False)


class TokenPayload(BaseModel):
    sub: str  # Username
    exp: datetime  # Expiration time
    role: str = "user"  # User role, default is regular user
    metadata: dict = {}  # Additional metadata


class AuthHandler:
    def __init__(self):
        self.secret = global_args.token_secret
        self.algorithm = global_args.jwt_algorithm
        self.expire_hours = global_args.token_expire_hours
        self.guest_expire_hours = global_args.guest_token_expire_hours
        # Keep old accounts for backward compatibility or simple local test
        self.accounts = {}
        auth_accounts = global_args.auth_accounts
        if auth_accounts and auth_accounts != "admin:admin123":
             for account in auth_accounts.split(","):
                username, password = account.split(":", 1)
                self.accounts[username] = password

        # OAuth Configs
        self.oauth_configs = {
            "github": {
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "authorize_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_info_url": "https://api.github.com/user",
                "scope": "read:user user:email",
            },
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_info_url": "https://www.googleapis.com/oauth2/v3/userinfo",
                "scope": "openid email profile",
            },
            "facebook": {
                "client_id": os.getenv("FACEBOOK_CLIENT_ID"),
                "client_secret": os.getenv("FACEBOOK_CLIENT_SECRET"),
                "authorize_url": "https://www.facebook.com/v12.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v12.0/oauth/access_token",
                "user_info_url": "https://graph.facebook.com/me?fields=id,name,email",
                "scope": "email,public_profile",
            },
        }

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        if not hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def create_token(
        self,
        username: str,
        role: str = "user",
        custom_expire_hours: int = None,
        metadata: dict = None,
    ) -> str:
        """
        Create JWT token

        Args:
            username: Username
            role: User role, default is "user", guest is "guest"
            custom_expire_hours: Custom expiration time (hours), if None use default value
            metadata: Additional metadata

        Returns:
            str: Encoded JWT token
        """
        # Choose default expiration time based on role
        if custom_expire_hours is None:
            if role == "guest":
                expire_hours = self.guest_expire_hours
            else:
                expire_hours = self.expire_hours
        else:
            expire_hours = custom_expire_hours

        expire = datetime.utcnow() + timedelta(hours=expire_hours)

        # Create payload
        payload = TokenPayload(
            sub=username, exp=expire, role=role, metadata=metadata or {}
        )

        return jwt.encode(payload.dict(), self.secret, algorithm=self.algorithm)

    def validate_token(self, token: str) -> dict:
        """
        Validate JWT token

        Args:
            token: JWT token

        Returns:
            dict: Dictionary containing user information

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            expire_timestamp = payload["exp"]
            expire_time = datetime.utcfromtimestamp(expire_timestamp)

            if datetime.utcnow() > expire_time:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
                )

            # Return complete payload instead of just username
            return {
                "username": payload["sub"],
                "role": payload.get("role", "user"),
                "metadata": payload.get("metadata", {}),
                "exp": expire_time,
            }
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    async def get_oauth_login_url(self, provider: str, callback_url: str) -> str:
        """Get OAuth login URL"""
        config = self.oauth_configs.get(provider)
        if not config or not config["client_id"]:
            raise HTTPException(status_code=400, detail=f"OAuth provider {provider} not configured")

        params = {
            "client_id": config["client_id"],
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": config["scope"],
            "access_type": "offline",  # For Google refresh token
            "prompt": "consent",       # For Google to ensure refresh token
        }
        
        # Build query string manually to avoid encoding issues with specific providers if any
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{config['authorize_url']}?{query_string}"

    async def get_oauth_user_info(self, provider: str, code: str, callback_url: str) -> dict:
        """Exchange code for token and get user info"""
        config = self.oauth_configs.get(provider)
        if not config:
            raise HTTPException(status_code=400, detail=f"OAuth provider {provider} not configured")

        async with httpx.AsyncClient() as client:
            # 1. Exchange code for token
            token_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url,
            }
            headers = {"Accept": "application/json"}
            
            try:
                token_response = await client.post(config["token_url"], data=token_data, headers=headers)
                token_response.raise_for_status()
                token_json = token_response.json()
                access_token = token_json.get("access_token")
                
                if not access_token:
                     # Some providers like Facebook return errors in body with 200 OK sometimes? (Actually FB returns JSON usually)
                     # Or github returns query string if header not set (we set Accept: json)
                     raise ValueError(f"No access token in response: {token_response.text}")
                     
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to get access token: {str(e)}")

            # 2. Get user info
            user_headers = {"Authorization": f"Bearer {access_token}"}
            try:
                user_response = await client.get(config["user_info_url"], headers=user_headers)
                user_response.raise_for_status()
                user_info = user_response.json()
                
                # Normalize user info
                if provider == "github":
                    username = f"github_{user_info['id']}"
                    email = user_info.get("email")
                elif provider == "google":
                    username = f"google_{user_info['sub']}" # sub is unique ID
                    email = user_info.get("email")
                elif provider == "facebook":
                    username = f"facebook_{user_info['id']}"
                    email = user_info.get("email")
                else:
                     username = user_info.get("id")
                     email = None

                return {
                    "username": username,
                    "email": email,
                    "provider": provider,
                    "provider_id": str(user_info.get("id") or user_info.get("sub"))
                }

            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to fetch user info: {str(e)}")


auth_handler = AuthHandler()
