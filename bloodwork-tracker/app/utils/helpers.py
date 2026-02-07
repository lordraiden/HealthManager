from datetime import datetime, timedelta
from typing import Dict, Any, List
import re


def format_date(date_obj: datetime, format_str: str = "%Y-%m-%d") -> str:
    """Format a datetime object to a string"""
    return date_obj.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> datetime:
    """Parse a date string to a datetime object"""
    return datetime.strptime(date_str, format_str)


def sanitize_input(input_str: str) -> str:
    """Remove potentially harmful characters from input"""
    if input_str is None:
        return None
    
    # Remove script tags and other potentially harmful content
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', input_str, flags=re.IGNORECASE)
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'vbscript:', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized.strip()


def paginate_results(results: List[Any], page: int, per_page: int) -> Dict[str, Any]:
    """Paginate a list of results"""
    total = len(results)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_items = results[start_idx:end_idx]
    
    return {
        "items": paginated_items,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
        "current_page": page,
        "per_page": per_page
    }


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def safe_get(dictionary: Dict[str, Any], key_path: str, default: Any = None, sep: str = '.') -> Any:
    """Safely get a value from a nested dictionary using dot notation"""
    keys = key_path.split(sep)
    current = dictionary
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def calculate_age(birth_date: datetime) -> int:
    """Calculate age from birth date"""
    today = datetime.today()
    age = today.year - birth_date.year
    
    # Adjust if birthday hasn't occurred this year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    
    return age


def format_decimal(value: float, places: int = 2) -> str:
    """Format a decimal value to specified number of places"""
    return f"{value:.{places}f}"


def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def generate_slug(text: str) -> str:
    """Generate URL-friendly slug from text"""
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def mask_sensitive_data(data: str, visible_chars: int = 2, mask_char: str = '*') -> str:
    """Mask sensitive data like SSN or credit card numbers"""
    if not data or len(data) <= visible_chars * 2:
        return mask_char * len(data) if data else ''
    
    start_visible = data[:visible_chars]
    end_visible = data[-visible_chars:]
    masked_part = mask_char * (len(data) - visible_chars * 2)
    
    return f"{start_visible}{masked_part}{end_visible}"


def get_time_diff(start_time: datetime, end_time: datetime) -> Dict[str, int]:
    """Get time difference in various units"""
    diff = end_time - start_time
    
    total_seconds = int(diff.total_seconds())
    days = diff.days
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return {
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'total_seconds': total_seconds
    }