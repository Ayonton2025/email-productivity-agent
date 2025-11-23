import os
import base64
import json
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import msal
import requests
from datetime import datetime
import email as email_lib
from email.header import decode_header

class EmailProviderService:
    def __init__(self):
        self.gmail_service = None
        self.outlook_service = None
        
    # Gmail Integration - OAuth Methods
    async def authenticate_gmail_with_token(self, access_token: str, refresh_token: str = None) -> bool:
        """Authenticate with Gmail using OAuth tokens"""
        try:
            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=None,
                client_secret=None,
                scopes=['https://www.googleapis.com/auth/gmail.readonly',
                       'https://www.googleapis.com/auth/gmail.modify']
            )
            
            # Test the credentials
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            
            # Make a simple API call to verify credentials work
            self.gmail_service.users().getProfile(userId='me').execute()
            
            return True
            
        except HttpError as error:
            print(f'Gmail authentication error: {error}')
            return False
        except Exception as e:
            print(f'Gmail token validation error: {e}')
            return False

    def get_gmail_auth_url(self, client_id: str, redirect_uri: str) -> str:
        """Generate Gmail OAuth URL"""
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
                 'https://www.googleapis.com/auth/gmail.modify']
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = redirect_uri
        
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        return auth_url

    async def exchange_gmail_code(self, client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for tokens"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=['https://www.googleapis.com/auth/gmail.readonly',
                       'https://www.googleapis.com/auth/gmail.modify']
            )
            flow.redirect_uri = redirect_uri
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                'scopes': credentials.scopes
            }
        except Exception as e:
            print(f'Token exchange error: {e}')
            raise

    # Legacy method for backward compatibility
    async def authenticate_gmail(self, credentials_file: str, token_file: str) -> bool:
        """Authenticate with Gmail API (legacy method)"""
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify']
        
        creds = None
        
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            return True
        except HttpError as error:
            print(f'Gmail authentication error: {error}')
            return False
    
    async def fetch_gmail_emails(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail"""
        if not self.gmail_service:
            return []
        
        try:
            results = self.gmail_service.users().messages().list(
                userId='me', 
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.gmail_service.users().messages().get(
                    userId='me', 
                    id=message['id'],
                    format='full'
                ).execute()
                
                email_data = self._parse_gmail_message(msg)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f'Error fetching Gmail emails: {error}')
            return []
    
    def _parse_gmail_message(self, message: Dict) -> Optional[Dict[str, Any]]:
        """Parse Gmail message into standardized format"""
        try:
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), datetime.now().isoformat())
            
            # Extract body
            body = self._extract_gmail_body(message['payload'])
            
            return {
                'id': message['id'],
                'sender': sender,
                'subject': subject,
                'body': body,
                'timestamp': date,
                'provider': 'gmail',
                'raw_data': message
            }
        except Exception as e:
            print(f"Error parsing Gmail message: {e}")
            return None
    
    def _extract_gmail_body(self, payload: Dict) -> str:
        """Extract email body from Gmail payload"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        
        if 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            return base64.urlsafe_b64decode(data).decode('utf-8')
        
        return "No body content"
    
    # Outlook Integration
    async def authenticate_outlook(self, client_id: str, client_secret: str, tenant_id: str) -> bool:
        """Authenticate with Outlook/Microsoft Graph API"""
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )
        
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            self.outlook_access_token = result["access_token"]
            return True
        return False
    
    async def fetch_outlook_emails(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch emails from Outlook"""
        if not hasattr(self, 'outlook_access_token'):
            return []
        
        headers = {
            'Authorization': f'Bearer {self.outlook_access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            url = f"https://graph.microsoft.com/v1.0/me/messages?$top={max_results}&$select=subject,from,receivedDateTime,body,id"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            emails = []
            
            for message in data.get('value', []):
                email_data = self._parse_outlook_message(message)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except requests.RequestException as error:
            print(f'Error fetching Outlook emails: {error}')
            return []
    
    def _parse_outlook_message(self, message: Dict) -> Optional[Dict[str, Any]]:
        """Parse Outlook message into standardized format"""
        try:
            return {
                'id': message['id'],
                'sender': message['from']['emailAddress']['address'],
                'subject': message.get('subject', 'No Subject'),
                'body': message['body'].get('content', ''),
                'timestamp': message['receivedDateTime'],
                'provider': 'outlook',
                'raw_data': message
            }
        except Exception as e:
            print(f"Error parsing Outlook message: {e}")
            return None
    
    async def send_email_reply(self, provider: str, original_email_id: str, draft_content: Dict[str, str]) -> bool:
        """Send email reply through the respective provider"""
        if provider == 'gmail' and self.gmail_service:
            return await self._send_gmail_reply(original_email_id, draft_content)
        elif provider == 'outlook' and hasattr(self, 'outlook_access_token'):
            return await self._send_outlook_reply(original_email_id, draft_content)
        return False
    
    async def _send_gmail_reply(self, original_email_id: str, draft_content: Dict[str, str]) -> bool:
        """Send reply through Gmail"""
        try:
            message = self._create_gmail_message(draft_content)
            self.gmail_service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            return True
        except HttpError as error:
            print(f'Error sending Gmail reply: {error}')
            return False
    
    async def _send_outlook_reply(self, original_email_id: str, draft_content: Dict[str, str]) -> bool:
        """Send reply through Outlook"""
        try:
            message = self._create_outlook_message(draft_content)
            headers = {
                'Authorization': f'Bearer {self.outlook_access_token}',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                'https://graph.microsoft.com/v1.0/me/sendMail',
                headers=headers,
                json=message
            )
            return response.status_code == 202
        except requests.RequestException as error:
            print(f'Error sending Outlook reply: {error}')
            return False
    
    def _create_gmail_message(self, draft_content: Dict[str, str]) -> Dict:
        from email.mime.text import MIMEText
        import base64

        message = MIMEText(draft_content.get('body', ''))
        message['to'] = draft_content.get('recipient', '')
        message['from'] = 'me'
        message['subject'] = draft_content.get('subject', 'No Subject')
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}

    def _create_outlook_message(self, draft_content: Dict[str, str]) -> Dict:
        return {
            "message": {
                "subject": draft_content.get('subject', 'No Subject'),
                "body": {
                    "contentType": "Text",
                    "content": draft_content.get('body', '')
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": draft_content.get('recipient', '')
                        }
                    }
                ]
            }
        }