import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import email.utils
from urllib.parse import urlparse

class EmailValidator:
    """Email validation utilities"""
    
    @staticmethod
    def validate_email_format(email_address: str) -> bool:
        """Validate email format using RFC 5322"""
        if not email_address or len(email_address) > 254:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email_address))
    
    @staticmethod
    def validate_email_headers(headers: Dict[str, str]) -> List[str]:
        """Validate email headers and return list of issues"""
        issues = []
        
        # Check required headers
        required_headers = ['From', 'Subject']
        for header in required_headers:
            if header not in headers:
                issues.append(f"Missing required header: {header}")
        
        # Validate From header
        if 'From' in headers:
            try:
                email.utils.parseaddr(headers['From'])
            except (ValueError, AttributeError):
                issues.append("Invalid From header format")
        
        # Validate Date header if present
        if 'Date' in headers:
            try:
                email.utils.parsedate_to_datetime(headers['Date'])
            except (ValueError, TypeError):
                issues.append("Invalid Date header format")
        
        return issues
    
    @staticmethod
    def sanitize_email_content(content: str) -> str:
        """Sanitize email content to prevent XSS and injection attacks"""
        if not content:
            return ""
        
        # Remove script tags and event handlers
        sanitized = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', content, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+=\s*["\'][^"\']*["\']', '', sanitized)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'vbscript:', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized

class PromptValidator:
    """Prompt template validation utilities"""
    
    @staticmethod
    def validate_prompt_template(template_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate prompt template structure"""
        errors = []
        
        required_fields = ['name', 'template', 'category']
        for field in required_fields:
            if field not in template_data or not template_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate category
        valid_categories = ['categorization', 'action_extraction', 'reply_draft', 'summary', 'analysis']
        if 'category' in template_data and template_data['category'] not in valid_categories:
            errors.append(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        
        # Validate template length
        if 'template' in template_data:
            template = template_data['template']
            if len(template) < 10:
                errors.append("Prompt template too short (minimum 10 characters)")
            if len(template) > 10000:
                errors.append("Prompt template too long (maximum 10,000 characters)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_prompt_parameters(parameters: Dict[str, Any]) -> bool:
        """Validate prompt parameters structure"""
        if not isinstance(parameters, dict):
            return False
        
        for param_name, param_config in parameters.items():
            if not isinstance(param_config, dict):
                return False
            
            required_config_fields = ['type', 'required', 'description']
            for field in required_config_fields:
                if field not in param_config:
                    return False
            
            # Validate type
            valid_types = ['string', 'number', 'boolean', 'array', 'object']
            if param_config['type'] not in valid_types:
                return False
        
        return True

class JSONValidator:
    """JSON validation utilities"""
    
    @staticmethod
    def validate_json_structure(data: Any, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate JSON data against a simple schema"""
        errors = []
        
        if not isinstance(data, type(schema.get('type', type(None)))):
            errors.append(f"Expected type {schema.get('type')}, got {type(data)}")
            return False, errors
        
        if schema.get('type') == 'object':
            required_fields = schema.get('required', [])
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            properties = schema.get('properties', {})
            for field, value in data.items():
                if field in properties:
                    field_schema = properties[field]
                    is_valid, field_errors = JSONValidator.validate_json_structure(value, field_schema)
                    if not is_valid:
                        errors.extend([f"{field}.{error}" for error in field_errors])
        
        elif schema.get('type') == 'array':
            items_schema = schema.get('items', {})
            for i, item in enumerate(data):
                is_valid, item_errors = JSONValidator.validate_json_structure(item, items_schema)
                if not is_valid:
                    errors.extend([f"[{i}].{error}" for error in item_errors])
        
        # Validate constraints
        if 'minLength' in schema and len(str(data)) < schema['minLength']:
            errors.append(f"Value too short (minimum {schema['minLength']} characters)")
        
        if 'maxLength' in schema and len(str(data)) > schema['maxLength']:
            errors.append(f"Value too long (maximum {schema['maxLength']} characters)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def safe_json_loads(json_string: str, default: Any = None) -> Any:
        """Safely load JSON with error handling"""
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError, ValueError):
            return default

class URLValidator:
    """URL validation utilities"""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def is_safe_url(url: str, allowed_domains: List[str] = None) -> bool:
        """Check if URL is safe (not malicious)"""
        if not URLValidator.validate_url(url):
            return False
        
        try:
            result = urlparse(url)
            
            # Check for dangerous protocols
            dangerous_schemes = ['javascript', 'vbscript', 'data']
            if result.scheme.lower() in dangerous_schemes:
                return False
            
            # Check against allowed domains if provided
            if allowed_domains and result.netloc not in allowed_domains:
                return False
            
            return True
        except Exception:
            return False