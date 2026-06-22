"""
Multi-Provider Email Service

Abstract service for handling multiple email providers (Gmail, Outlook, Yahoo).
Provides unified interface for OAuth, email fetching, and sync operations.
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailProvider(str, Enum):
    """Supported email providers"""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    YAHOO = "yahoo"


class BaseEmailProvider(ABC):
    """Abstract base class for email providers"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.service = None
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Verify that credentials are valid"""
        pass
    
    @abstractmethod
    async def fetch_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch messages from the provider"""
        pass
    
    @abstractmethod
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get a specific message"""
        pass
    
    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        pass
    
    @abstractmethod
    async def setup_push_notifications(self, webhook_url: str) -> bool:
        """Setup push notifications for the account"""
        pass


class GmailProvider(BaseEmailProvider):
    """Gmail provider implementation using Google API"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.provider_name = EmailProvider.GMAIL
    
    async def authenticate(self) -> bool:
        """Verify Gmail access token is valid"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=self.access_token)
            auth_request = Request()
            creds.refresh(auth_request)
            
            logger.info("✅ Gmail credentials verified")
            return True
        
        except Exception as e:
            logger.error(f"❌ Gmail authentication failed: {e}")
            return False
    
    async def fetch_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent messages from Gmail"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=self.access_token)
            service = build("gmail", "v1", credentials=creds)
            
            # Fetch message IDs
            results = service.users().messages().list(userId="me", maxResults=limit).execute()
            messages = results.get("messages", [])
            
            # Fetch full message details
            full_messages = []
            for msg in messages:
                try:
                    message = service.users().messages().get(
                        userId="me", id=msg["id"], format="full"
                    ).execute()
                    full_messages.append(message)
                except Exception as e:
                    logger.warning(f"Failed to fetch message {msg['id']}: {e}")
            
            logger.info(f"✅ Fetched {len(full_messages)} messages from Gmail")
            return full_messages
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch Gmail messages: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get a specific message from Gmail"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=self.access_token)
            service = build("gmail", "v1", credentials=creds)
            
            message = service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()
            
            return message
        
        except Exception as e:
            logger.error(f"❌ Failed to get message {message_id}: {e}")
            return {}
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a Gmail message as read"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=self.access_token)
            service = build("gmail", "v1", credentials=creds)
            
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            
            logger.debug(f"✅ Marked Gmail message {message_id} as read")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to mark message as read: {e}")
            return False
    
    async def setup_push_notifications(self, webhook_url: str) -> bool:
        """Setup Gmail push notifications via Pub/Sub"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=self.access_token)
            service = build("gmail", "v1", credentials=creds)
            
            # Watch the mailbox
            service.users().watch(
                userId="me",
                body={"topicName": webhook_url}
            ).execute()
            
            logger.info(f"✅ Setup Gmail push notifications")
            return True
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup Gmail push: {e}")
            return False


class OutlookProvider(BaseEmailProvider):
    """Outlook/Office365 provider implementation using Microsoft Graph API"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.provider_name = EmailProvider.OUTLOOK
        self.base_url = "https://graph.microsoft.com/v1.0"
    
    async def authenticate(self) -> bool:
        """Verify Outlook access token is valid"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                async with session.get(f"{self.base_url}/me", headers=headers) as resp:
                    if resp.status == 200:
                        logger.info("✅ Outlook credentials verified")
                        return True
                    else:
                        logger.error(f"Outlook auth failed: {resp.status}")
                        return False
        
        except Exception as e:
            logger.error(f"❌ Outlook authentication failed: {e}")
            return False
    
    async def fetch_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent messages from Outlook"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                
                # Get messages
                url = f"{self.base_url}/me/mailFolders/inbox/messages?$top={limit}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        messages = data.get("value", [])
                        logger.info(f"✅ Fetched {len(messages)} messages from Outlook")
                        return messages
                    else:
                        logger.error(f"Failed to fetch Outlook messages: {resp.status}")
                        return []
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch Outlook messages: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get a specific message from Outlook"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                
                url = f"{self.base_url}/me/messages/{message_id}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        message = await resp.json()
                        return message
                    else:
                        logger.error(f"Failed to get Outlook message: {resp.status}")
                        return {}
        
        except Exception as e:
            logger.error(f"❌ Failed to get Outlook message {message_id}: {e}")
            return {}
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark an Outlook message as read"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.base_url}/me/messages/{message_id}"
                body = {"isRead": True}
                
                async with session.patch(url, headers=headers, json=body) as resp:
                    if resp.status in [200, 204]:
                        logger.debug(f"✅ Marked Outlook message {message_id} as read")
                        return True
                    else:
                        logger.error(f"Failed to mark message as read: {resp.status}")
                        return False
        
        except Exception as e:
            logger.error(f"❌ Failed to mark Outlook message as read: {e}")
            return False
    
    async def setup_push_notifications(self, webhook_url: str) -> bool:
        """Setup Outlook push notifications via Change Notifications"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.base_url}/subscriptions"
                body = {
                    "changeType": "created",
                    "notificationUrl": webhook_url,
                    "resource": "me/mailFolders('inbox')/messages",
                    "expirationDateTime": datetime.utcnow().isoformat() + "Z",
                }
                
                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status == 201:
                        logger.info("✅ Setup Outlook push notifications")
                        return True
                    else:
                        result = await resp.json()
                        logger.warning(f"⚠️ Failed to setup Outlook push: {result}")
                        return False
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup Outlook push: {e}")
            return False


class YahooProvider(BaseEmailProvider):
    """Yahoo provider implementation using Yahoo Mail API"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.provider_name = EmailProvider.YAHOO
        self.base_url = "https://api.mail.yahoo.com"
    
    async def authenticate(self) -> bool:
        """Verify Yahoo access token is valid"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                async with session.get(f"{self.base_url}/user", headers=headers) as resp:
                    if resp.status == 200:
                        logger.info("✅ Yahoo credentials verified")
                        return True
                    else:
                        logger.error(f"Yahoo auth failed: {resp.status}")
                        return False
        
        except Exception as e:
            logger.error(f"❌ Yahoo authentication failed: {e}")
            return False
    
    async def fetch_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent messages from Yahoo"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                
                # Get messages
                url = f"{self.base_url}/user/messages?count={limit}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        messages = data.get("messages", [])
                        logger.info(f"✅ Fetched {len(messages)} messages from Yahoo")
                        return messages
                    else:
                        logger.error(f"Failed to fetch Yahoo messages: {resp.status}")
                        return []
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch Yahoo messages: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get a specific message from Yahoo"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                
                url = f"{self.base_url}/user/messages/{message_id}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        message = await resp.json()
                        return message
                    else:
                        logger.error(f"Failed to get Yahoo message: {resp.status}")
                        return {}
        
        except Exception as e:
            logger.error(f"❌ Failed to get Yahoo message {message_id}: {e}")
            return {}
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a Yahoo message as read"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.base_url}/user/messages/{message_id}"
                body = {"read": True}
                
                async with session.patch(url, headers=headers, json=body) as resp:
                    if resp.status in [200, 204]:
                        logger.debug(f"✅ Marked Yahoo message {message_id} as read")
                        return True
                    else:
                        logger.error(f"Failed to mark message as read: {resp.status}")
                        return False
        
        except Exception as e:
            logger.error(f"❌ Failed to mark Yahoo message as read: {e}")
            return False
    
    async def setup_push_notifications(self, webhook_url: str) -> bool:
        """Setup Yahoo push notifications"""
        try:
            import aiohttp  # type: ignore[import]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.base_url}/user/register_webhook"
                body = {"webhookUrl": webhook_url}
                
                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status == 200:
                        logger.info("✅ Setup Yahoo push notifications")
                        return True
                    else:
                        logger.warning(f"⚠️ Failed to setup Yahoo push: {resp.status}")
                        return False
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup Yahoo push: {e}")
            return False


class MultiProviderService:
    """Service for handling multiple email providers"""
    
    @staticmethod
    def get_provider(
        provider_name: str,
        access_token: str,
        refresh_token: Optional[str] = None
    ) -> Optional[BaseEmailProvider]:
        """
        Factory method to get the appropriate email provider.
        
        Args:
            provider_name: Provider name (gmail, outlook, yahoo)
            access_token: OAuth access token
            refresh_token: OAuth refresh token
        
        Returns:
            Provider instance or None
        """
        try:
            provider_lower = provider_name.lower()
            
            if provider_lower == EmailProvider.GMAIL.value:
                return GmailProvider(access_token, refresh_token)
            
            elif provider_lower == EmailProvider.OUTLOOK.value:
                return OutlookProvider(access_token, refresh_token)
            
            elif provider_lower == EmailProvider.YAHOO.value:
                return YahooProvider(access_token, refresh_token)
            
            else:
                logger.error(f"❌ Unknown provider: {provider_name}")
                return None
        
        except Exception as e:
            logger.error(f"❌ Failed to get provider: {e}")
            return None
    
    @staticmethod
    def get_provider_config(provider_name: str) -> Dict[str, Any]:
        """
        Get provider configuration (OAuth endpoints, scopes, etc.)
        
        Args:
            provider_name: Provider name
        
        Returns:
            Configuration dictionary
        """
        configs = {
            EmailProvider.GMAIL.value: {
                "display_name": "Gmail",
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/userinfo.email"
                ]
            },
            EmailProvider.OUTLOOK.value: {
                "display_name": "Outlook",
                "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                "scopes": [
                    "Mail.Read",
                    "Mail.ReadWrite",
                    "User.Read"
                ]
            },
            EmailProvider.YAHOO.value: {
                "display_name": "Yahoo Mail",
                "auth_url": "https://api.login.yahoo.com/oauth2/request_auth",
                "token_url": "https://api.login.yahoo.com/oauth2/get_token",
                "scopes": [
                    "mail-r",  # Read mail
                ]
            }
        }
        
        return configs.get(provider_name.lower(), {})
