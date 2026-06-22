"""
Elasticsearch Search Service

Provides full-text search across email content using Elasticsearch.
Handles indexing, searching, and result ranking.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Try to import Elasticsearch client
try:
    from elasticsearch import Elasticsearch  # type: ignore[import]
    from elasticsearch.helpers import bulk  # type: ignore[import]
    HAS_ELASTICSEARCH = True
except ImportError:
    HAS_ELASTICSEARCH = False
    logger.warning("⚠️ elasticsearch not installed, full-text search will be disabled")


class ElasticsearchService:
    """
    Service for managing Elasticsearch full-text search.
    
    Provides methods to:
    - Index emails for full-text search
    - Search across email content
    - Delete indexed emails
    - Manage index settings
    """
    
    INDEX_NAME = "emails"
    
    def __init__(self):
        """Initialize Elasticsearch connection"""
        self.enabled = HAS_ELASTICSEARCH
        self.client = None
        
        if self.enabled:
            try:
                # Get Elasticsearch configuration from environment
                es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
                es_port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
                es_url = f"http://{es_host}:{es_port}"
                
                self.client = Elasticsearch([es_url])
                
                # Validate connection
                if self.client.ping():
                    logger.info(f"✅ Connected to Elasticsearch at {es_url}")
                    self._create_index_if_needed()
                else:
                    logger.warning("⚠️ Failed to connect to Elasticsearch")
                    self.enabled = False
            
            except Exception as e:
                logger.warning(f"⚠️ Elasticsearch initialization failed: {e}")
                self.enabled = False
    
    def _create_index_if_needed(self):
        """Create Elasticsearch index if it doesn't exist"""
        try:
            if self.client.indices.exists(index=self.INDEX_NAME):
                logger.debug(f"Index '{self.INDEX_NAME}' already exists")
                return
            
            # Create index with custom analyzers and mappings
            index_settings = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "email_analyzer": {
                                "type": "standard",
                                "stopwords": "_english_"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "user_id": {"type": "keyword"},
                        "email_id": {"type": "keyword"},
                        "subject": {
                            "type": "text",
                            "analyzer": "email_analyzer",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "sender": {
                            "type": "text",
                            "analyzer": "email_analyzer",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "recipients": {
                            "type": "text",
                            "analyzer": "email_analyzer"
                        },
                        "body_text": {
                            "type": "text",
                            "analyzer": "email_analyzer"
                        },
                        "body_html": {
                            "type": "text",
                            "analyzer": "email_analyzer"
                        },
                        "received_at": {"type": "date"},
                        "ai_category": {"type": "keyword"},
                        "is_read": {"type": "boolean"},
                        "is_flagged": {"type": "boolean"},
                        "indexed_at": {"type": "date"}
                    }
                }
            }
            
            self.client.indices.create(index=self.INDEX_NAME, body=index_settings)
            logger.info(f"✅ Created Elasticsearch index '{self.INDEX_NAME}'")
        
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
    
    async def index_email(
        self,
        user_id: str,
        email_id: int,
        subject: str,
        sender: str,
        recipients: List[str],
        body_text: str,
        received_at: datetime,
        ai_category: Optional[str] = None
    ) -> bool:
        """
        Index an email for full-text search.
        
        Args:
            user_id: User ID
            email_id: Email ID
            subject: Email subject
            sender: Email sender
            recipients: List of recipient emails
            body_text: Email body text
            received_at: Email received timestamp
            ai_category: AI categorization (optional)
        
        Returns:
            True if successfully indexed
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            doc = {
                "user_id": user_id,
                "email_id": str(email_id),
                "subject": subject,
                "sender": sender,
                "recipients": " ".join(recipients),
                "body_text": body_text,
                "received_at": received_at.isoformat(),
                "ai_category": ai_category,
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Index with user_id:email_id as the document ID
            doc_id = f"{user_id}:{email_id}"
            self.client.index(
                index=self.INDEX_NAME,
                id=doc_id,
                body=doc
            )
            
            logger.debug(f"✅ Indexed email {email_id} for user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to index email {email_id}: {e}")
            return False
    
    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Full-text search across user's emails.
        
        Args:
            user_id: User ID
            query: Search query
            limit: Maximum results to return
            offset: Result offset for pagination
            filters: Additional filters (category, is_read, is_flagged, date_range)
        
        Returns:
            Dictionary with results and metadata
        """
        if not self.enabled or not self.client:
            return {"hits": [], "total": 0, "error": "Elasticsearch not available"}
        
        try:
            # Build the search query
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user_id": user_id}},
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "subject^3",  # Boost subject matches 3x
                                        "sender^2",   # Boost sender matches 2x
                                        "recipients",
                                        "body_text",
                                        "ai_category"
                                    ],
                                    "fuzziness": "AUTO"  # Allow fuzzy matching
                                }
                            }
                        ]
                    }
                },
                "from": offset,
                "size": limit,
                "sort": [{"received_at": {"order": "desc"}}]
            }
            
            # Apply optional filters
            if filters:
                if "category" in filters:
                    es_query["query"]["bool"]["must"].append(
                        {"term": {"ai_category": filters["category"]}}
                    )
                
                if "is_read" in filters:
                    es_query["query"]["bool"]["must"].append(
                        {"term": {"is_read": filters["is_read"]}}
                    )
                
                if "is_flagged" in filters:
                    es_query["query"]["bool"]["must"].append(
                        {"term": {"is_flagged": filters["is_flagged"]}}
                    )
                
                if "date_from" in filters and "date_to" in filters:
                    es_query["query"]["bool"]["must"].append({
                        "range": {
                            "received_at": {
                                "gte": filters["date_from"],
                                "lte": filters["date_to"]
                            }
                        }
                    })
            
            # Execute search
            response = self.client.search(index=self.INDEX_NAME, body=es_query)
            
            # Format results
            hits = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                hits.append({
                    "email_id": source["email_id"],
                    "subject": source["subject"],
                    "sender": source["sender"],
                    "received_at": source["received_at"],
                    "ai_category": source.get("ai_category"),
                    "snippet": (source["body_text"][:200] + "...") if source["body_text"] else "",
                    "score": hit["_score"]
                })
            
            return {
                "hits": hits,
                "total": response["hits"]["total"]["value"],
                "offset": offset,
                "limit": limit
            }
        
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {"hits": [], "total": 0, "error": str(e)}
    
    async def delete_email(self, user_id: str, email_id: int) -> bool:
        """
        Delete an email from the search index.
        
        Args:
            user_id: User ID
            email_id: Email ID
        
        Returns:
            True if successfully deleted
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            doc_id = f"{user_id}:{email_id}"
            self.client.delete(index=self.INDEX_NAME, id=doc_id)
            logger.debug(f"✅ Deleted email {email_id} from index")
            return True
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete email from index: {e}")
            return False
    
    async def delete_user_emails(self, user_id: str) -> int:
        """
        Delete all emails for a user from the search index.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of emails deleted
        """
        if not self.enabled or not self.client:
            return 0
        
        try:
            response = self.client.delete_by_query(
                index=self.INDEX_NAME,
                body={"query": {"term": {"user_id": user_id}}}
            )
            
            deleted_count = response["deleted"]
            logger.info(f"✅ Deleted {deleted_count} emails for user {user_id} from index")
            return deleted_count
        
        except Exception as e:
            logger.error(f"❌ Failed to delete user emails from index: {e}")
            return 0
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the search index.
        
        Returns:
            Dictionary with index statistics
        """
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            stats = self.client.indices.stats(index=self.INDEX_NAME)
            
            return {
                "enabled": True,
                "document_count": stats["indices"][self.INDEX_NAME]["primaries"]["docs"]["count"],
                "index_size_bytes": stats["indices"][self.INDEX_NAME]["primaries"]["store"]["size_in_bytes"],
                "status": stats["indices"][self.INDEX_NAME]["status"]
            }
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to get index stats: {e}")
            return {"enabled": True, "error": str(e)}


# Global Elasticsearch service instance
elasticsearch_service = ElasticsearchService()
