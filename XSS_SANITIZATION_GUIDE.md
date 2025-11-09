# XSS Sanitization Usage Guide

## Overview

The `sanitize_html_content()` function provides protection against Cross-Site Scripting (XSS) attacks by escaping dangerous HTML characters in user-generated content.

**Location**: `backend/src/utils/validators.py`

## When to Use

Apply HTML sanitization to **all user-generated text fields** that may be:
- Displayed in web interfaces
- Stored in databases and later rendered
- Included in API responses
- Used in notifications or emails

## Common Use Cases

### 1. Message Content

```python
from ...utils.validators import sanitize_html_content

@router.post("/agents/{agent_id}/messages")
async def create_message(
    agent_id: str,
    message_data: MessageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
):
    # Sanitize user-provided content
    sanitized_content = sanitize_html_content(message_data.content)

    # Store sanitized content
    await db.execute(
        "INSERT INTO messages (agent_id, content, user_id) VALUES ($1, $2, $3)",
        agent_id, sanitized_content, current_user["user_id"]
    )

    return {"status": "created", "content": sanitized_content}
```

### 2. Agent Descriptions

```python
@router.post("/agents/")
async def create_agent(
    agent_data: AgentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
):
    # Sanitize description field
    sanitized_description = sanitize_html_content(
        agent_data.description,
        max_length=5000  # Custom length limit
    )

    agent = Agent(
        name=agent_data.name,
        description=sanitized_description,
        created_by=current_user["user_id"]
    )

    db.add(agent)
    await db.commit()

    return agent
```

### 3. User Profile Fields

```python
@router.patch("/users/{user_id}")
async def update_user_profile(
    user_id: str,
    profile_data: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
):
    # Sanitize all text fields
    updates = {
        "bio": sanitize_html_content(profile_data.bio) if profile_data.bio else None,
        "status": sanitize_html_content(profile_data.status) if profile_data.status else None,
    }

    await db.execute(
        "UPDATE users SET bio = $1, status = $2 WHERE user_id = $3",
        updates["bio"], updates["status"], user_id
    )

    return {"status": "updated"}
```

### 4. Comments and Feedback

```python
@router.post("/agents/{agent_id}/feedback")
async def submit_feedback(
    agent_id: str,
    feedback_data: FeedbackCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
):
    # Sanitize feedback text
    sanitized_feedback = sanitize_html_content(feedback_data.comment)

    feedback = Feedback(
        agent_id=agent_id,
        user_id=current_user["user_id"],
        comment=sanitized_feedback,
        rating=feedback_data.rating
    )

    db.add(feedback)
    await db.commit()

    return {"status": "submitted"}
```

## What Gets Sanitized

The function escapes the following HTML entities:

| Character | Escaped As | Example |
|-----------|-----------|---------|
| `<` | `&lt;` | `<script>` → `&lt;script&gt;` |
| `>` | `&gt;` | `</div>` → `&lt;/div&gt;` |
| `&` | `&amp;` | `Tom & Jerry` → `Tom &amp; Jerry` |
| `"` | `&quot;` | `Say "Hello"` → `Say &quot;Hello&quot;` |
| `'` | `&#x27;` | `It's` → `It&#x27;s` |

## Attack Vectors Prevented

### 1. Script Injection
```python
# Input
malicious_input = "<script>fetch('/api/admin/delete-all')</script>"

# Output (safe)
sanitized = sanitize_html_content(malicious_input)
# "&lt;script&gt;fetch('/api/admin/delete-all')&lt;/script&gt;"
```

### 2. Event Handler Injection
```python
# Input
malicious_input = '<img src=x onerror=alert("XSS")>'

# Output (safe)
sanitized = sanitize_html_content(malicious_input)
# "&lt;img src=x onerror=alert(&quot;XSS&quot;)&gt;"
```

### 3. SVG-Based XSS
```python
# Input
malicious_input = '<svg onload=alert("XSS")>'

# Output (safe)
sanitized = sanitize_html_content(malicious_input)
# "&lt;svg onload=alert(&quot;XSS&quot;)&gt;"
```

### 4. Data Protocol Injection
```python
# Input
malicious_input = '<a href="javascript:alert(\'XSS\')">Click</a>'

# Output (safe)
sanitized = sanitize_html_content(malicious_input)
# "&lt;a href=&quot;javascript:alert(&#x27;XSS&#x27;)&quot;&gt;Click&lt;/a&gt;"
```

## Configuration Options

### Custom Length Limits

```python
# Default: 10,000 characters
sanitize_html_content(content)

# Custom limit: 500 characters
sanitize_html_content(content, max_length=500)

# Longer limit for blog posts: 50,000 characters
sanitize_html_content(content, max_length=50000)
```

### Conditional Sanitization

```python
# Only sanitize if content is provided
if user_input.comment:
    sanitized_comment = sanitize_html_content(user_input.comment)
else:
    sanitized_comment = None
```

## Fields That Should Be Sanitized

### ✅ Always Sanitize

- User messages and chat content
- Comments and feedback
- User profile fields (bio, status, description)
- Agent descriptions and metadata
- Notification messages
- Error messages containing user input
- Search queries that are displayed back
- Any field displayed in HTML context

### ❌ Don't Sanitize

- Email addresses (use email validator instead)
- URLs (use URL validator instead)
- Numeric values
- Dates and timestamps
- Boolean values
- Enum values (already restricted)
- IDs (use ID validators instead)

## Pydantic Model Integration

For automatic sanitization, create a Pydantic validator:

```python
from pydantic import BaseModel, validator
from src.utils.validators import sanitize_html_content

class MessageCreate(BaseModel):
    content: str
    message_type: str

    @validator('content')
    def sanitize_content(cls, v):
        """Automatically sanitize content field."""
        if v:
            return sanitize_html_content(v)
        return v

class AgentCreate(BaseModel):
    name: str
    description: Optional[str]

    @validator('description')
    def sanitize_description(cls, v):
        """Automatically sanitize description field."""
        if v:
            return sanitize_html_content(v, max_length=5000)
        return v
```

## Error Handling

The function raises `HTTPException` in these cases:

```python
# Non-string input
try:
    sanitize_html_content(123)
except HTTPException as e:
    # e.status_code == 400
    # e.detail == "Content must be a string"

# Content too long
try:
    sanitize_html_content("a" * 20000)  # Over 10,000 char limit
except HTTPException as e:
    # e.status_code == 400
    # e.detail == "Content too long (max 10000 characters)"
```

## Testing Sanitization

Always test your sanitization:

```python
import pytest
from src.utils.validators import sanitize_html_content

def test_xss_prevention():
    """Test that XSS attacks are prevented."""
    malicious = "<script>alert('XSS')</script>"
    sanitized = sanitize_html_content(malicious)

    # Ensure no executable script tags
    assert "<script>" not in sanitized
    assert "alert" in sanitized  # Content preserved
    assert "&lt;script&gt;" in sanitized  # But escaped
```

## Performance Considerations

- **Minimal overhead**: HTML escaping is very fast (O(n) single pass)
- **Safe to call repeatedly**: Idempotent operation
- **Database storage**: Store sanitized content to avoid repeated sanitization
- **Caching**: Sanitize once, cache if needed

## Migration Strategy

If adding sanitization to an existing system:

### 1. Sanitize on Write (Recommended)

```python
# New data is sanitized before storage
sanitized = sanitize_html_content(new_content)
db.save(sanitized)
```

### 2. Sanitize on Read (Temporary)

```python
# Sanitize existing data when retrieved
raw_content = db.get_content()
safe_content = sanitize_html_content(raw_content)
return safe_content
```

### 3. Batch Migration

```python
# One-time script to sanitize existing data
async def migrate_existing_content():
    records = await db.execute("SELECT id, content FROM messages")

    for record in records:
        sanitized = sanitize_html_content(record.content)
        await db.execute(
            "UPDATE messages SET content = $1 WHERE id = $2",
            sanitized, record.id
        )
```

## Security Checklist

- [ ] Identify all user-generated text fields
- [ ] Add `sanitize_html_content()` to write endpoints
- [ ] Add Pydantic validators for automatic sanitization
- [ ] Write tests for XSS prevention
- [ ] Review existing data for unsanitized content
- [ ] Document which fields are sanitized
- [ ] Add sanitization to new features

## Additional Resources

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [HTML Entity Reference](https://html.spec.whatwg.org/multipage/named-characters.html)
- [Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

## Support

For questions or issues with XSS sanitization:
1. Check this guide
2. Review test cases in `backend/tests/test_validators.py`
3. Consult `backend/src/utils/validators.py` implementation
