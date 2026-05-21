"""
Gmail API handler with optimizations:
- Pagination support
- Batch requests
- Rate limiting with exponential backoff
- Proper error handling
"""
import os
import base64
import re
import time
import logging
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

logger = logging.getLogger(__name__)


class GmailHandler:
    """Handle Gmail API operations with optimizations"""
    
    def __init__(self):
        self.service = None
        self.creds = None
        
    def authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2"""
        if os.path.exists(config.TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(
                config.TOKEN_FILE, config.SCOPES
            )
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials")
                self.creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.CREDENTIALS_FILE, config.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            with open(config.TOKEN_FILE, 'w') as token:
                token.write(self.creds.to_json())
                logger.info("Credentials saved to token.json")
        
        self.service = build('gmail', 'v1', credentials=self.creds)
        logger.info("Gmail API service initialized")
    
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(config.INITIAL_BACKOFF * (2 ** attempt), config.MAX_BACKOFF)
        return delay
    
    def _execute_with_retry(self, request, max_retries: int = config.MAX_RETRIES):
        """Execute API request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    if attempt < max_retries - 1:
                        delay = self._exponential_backoff(attempt)
                        logger.warning(
                            f"Rate limit/server error. Retrying in {delay}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries reached: {e}")
                        raise
                else:
                    logger.error(f"HTTP error: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
    
    def get_all_messages(self, query: str) -> List[dict]:
        """
        Fetch all messages matching query with pagination support
        
        Args:
            query: Gmail search query
            
        Returns:
            List of message objects with id and threadId
        """
        if not self.service:
            self.authenticate()
        
        messages = []
        page_token = None
        page_count = 0
        
        logger.info(f"Searching for messages with query: {query}")
        
        while True:
            try:
                request = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    pageToken=page_token
                )
                results = self._execute_with_retry(request)
                
                page_messages = results.get('messages', [])
                messages.extend(page_messages)
                page_count += 1
                
                logger.info(
                    f"Page {page_count}: Found {len(page_messages)} messages "
                    f"(Total: {len(messages)})"
                )
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                break
        
        logger.info(f"Total messages found: {len(messages)}")
        return messages
    
    def get_message_body(self, message_id: str) -> str:
        """
        Fetch message body with optimized format
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Decoded message body text
        """
        try:
            request = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            )
            message = self._execute_with_retry(request)
            
            payload = message.get('payload', {})
            body = ""
            
            # Handle multipart messages
            parts = payload.get('parts')
            if parts:
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
            else:
                # Single part message
                data = payload.get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            return body
            
        except Exception as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return ""
    
    def extract_removal_links(self, body: str) -> List[str]:
        """
        Extract removal links from email body
        
        Args:
            body: Email body text
            
        Returns:
            List of removal links found
        """
        links = re.findall(config.REMOVAL_LINK_PATTERN, body)
        return links
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message by moving it to trash
        
        Args:
            message_id: Gmail message ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.service.users().messages().trash(
                userId='me',
                id=message_id
            )
            self._execute_with_retry(request)
            logger.info(f"Successfully deleted message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return False
    
    def delete_messages_batch(self, message_ids: List[str]) -> int:
        """
        Delete multiple messages in batch
        
        Args:
            message_ids: List of Gmail message IDs to delete
            
        Returns:
            Number of successfully deleted messages
        """
        if not message_ids:
            return 0
        
        deleted_count = 0
        total = len(message_ids)
        
        logger.info(f"Deleting {total} messages...")
        
        for idx, msg_id in enumerate(message_ids, 1):
            if self.delete_message(msg_id):
                deleted_count += 1
            
            if idx % 10 == 0:
                logger.info(f"Deleted {deleted_count}/{idx} messages")
        
        logger.info(f"Deletion complete: {deleted_count}/{total} messages deleted")
        return deleted_count
    
    def get_message_metadata(self, message_id: str) -> dict:
        """
        Fetch message metadata (subject, date)
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dict with 'subject' and 'date' keys
        """
        try:
            request = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Subject', 'Date']
            )
            message = self._execute_with_retry(request)
            
            headers = message.get('payload', {}).get('headers', [])
            metadata = {'subject': 'No Subject', 'date': 'Unknown'}
            
            for header in headers:
                name = header.get('name', '').lower()
                if name == 'subject':
                    metadata['subject'] = header.get('value', 'No Subject')
                elif name == 'date':
                    metadata['date'] = header.get('value', 'Unknown')
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching metadata for message {message_id}: {e}")
            return {'subject': 'Error fetching subject', 'date': 'Unknown'}
    
    def get_removal_links(self) -> tuple[List[str], dict[str, List[str]], dict[str, dict]]:
        """
        Main method to get all removal links from Gmail
        
        Returns:
            Tuple of (unique_links, link_to_message_ids_map, message_metadata)
            - unique_links: Deduplicated list of removal links
            - link_to_message_ids_map: Dict mapping each link to list of message IDs containing it
            - message_metadata: Dict mapping message ID to metadata (subject, date)
        """
        logger.info("Starting removal link extraction")
        
        # Authenticate if needed
        if not self.service:
            self.authenticate()
        
        # Get all matching messages
        messages = self.get_all_messages(config.GMAIL_QUERY)
        
        if not messages:
            logger.warning("No messages found matching query")
            return [], {}, {}
        
        # Extract links from all messages and track which messages contain which links
        link_to_messages = {}  # Maps link -> list of message IDs
        message_metadata = {}  # Maps message ID -> metadata
        processed = 0
        
        for msg in messages:
            try:
                body = self.get_message_body(msg['id'])
                links = self.extract_removal_links(body)
                
                if links:
                    # Get metadata for this message
                    if msg['id'] not in message_metadata:
                        message_metadata[msg['id']] = self.get_message_metadata(msg['id'])
                    
                    for link in links:
                        if link not in link_to_messages:
                            link_to_messages[link] = []
                        link_to_messages[link].append(msg['id'])
                    logger.debug(f"Found {len(links)} links in message {msg['id']}")
                
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"Processed {processed}/{len(messages)} messages")
                    
            except Exception as e:
                logger.error(f"Error processing message {msg['id']}: {e}")
                continue
        
        # Get unique links
        unique_links = list(link_to_messages.keys())
        total_messages_with_links = sum(len(msg_ids) for msg_ids in link_to_messages.values())
        
        logger.info(
            f"Extraction complete: {len(unique_links)} unique links "
            f"from {total_messages_with_links} messages"
        )
        
        return unique_links, link_to_messages, message_metadata

# Made with Bob
