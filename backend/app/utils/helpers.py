import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import re
import uuid

def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())

def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """Format timestamp for display"""
    if not timestamp:
        timestamp = datetime.utcnow()
    return timestamp.isoformat()

def parse_json_safely(json_str: str, default: Any = None) -> Any:
    """Safely parse JSON string with fallback"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def extract_email_parts(email_address: str) -> Dict[str, str]:
    """Extract name and domain from email address"""
    if not email_address or '@' not in email_address:
        return {"local": "", "domain": "", "full": email_address}
    
    local_part, domain = email_address.split('@', 1)
    return {
        "local": local_part,
        "domain": domain,
        "full": email_address
    }

def clean_email_body(body: str) -> str:
    """Clean and normalize email body text"""
    if not body:
        return ""
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', body.strip())
    
    # Remove common email signatures and forward headers
    lines = cleaned.split('\n')
    filtered_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip common signature markers
        if any(marker in line.lower() for marker in ['sent from', 'regards,', 'best,', 'thanks,', 'cheers,']):
            break
        # Skip forward headers
        if line.startswith('---') or line.startswith('___') or line.startswith('From:'):
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def calculate_priority_score(email_data: Dict[str, Any]) -> int:
    """Calculate priority score for email (0-100)"""
    score = 50  # Default medium priority
    
    # Adjust based on sender (you can expand this)
    important_domains = ['company.com', 'management.com', 'hr.com']
    sender_domain = extract_email_parts(email_data.get('sender', '')).get('domain', '')
    if any(domain in sender_domain for domain in important_domains):
        score += 20
    
    # Adjust based on subject keywords
    urgent_keywords = ['urgent', 'important', 'asap', 'action required', 'deadline']
    subject = email_data.get('subject', '').lower()
    if any(keyword in subject for keyword in urgent_keywords):
        score += 25
    
    # Adjust based on content length (longer emails might be more important)
    body = email_data.get('body', '')
    if len(body) > 500:
        score += 5
    elif len(body) < 50:
        score -= 10
    
    return max(0, min(100, score))

def format_priority(score: int) -> str:
    """Convert priority score to category"""
    if score >= 80:
        return "urgent"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    else:
        return "low"

async def async_retry(operation, max_retries: int = 3, delay: float = 1.0):
    """Retry an async operation with exponential backoff"""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
    
    raise last_exception

def validate_email_structure(email_data: Dict[str, Any]) -> List[str]:
    """Validate email data structure and return list of errors"""
    errors = []
    
    required_fields = ['sender', 'subject', 'body']
    for field in required_fields:
        if field not in email_data or not email_data[field]:
            errors.append(f"Missing required field: {field}")
    
    if 'sender' in email_data and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email_data['sender']):
        errors.append("Invalid sender email format")
    
    return errors

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"