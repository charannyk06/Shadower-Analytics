# Specification: Notification System

## Overview
Implement multi-channel notification system with templates, preferences, digest options, and delivery tracking for all analytics events and alerts.

## Technical Requirements

### Backend Implementation

#### Service: `services/notification_system.py`
```python
class NotificationSystem:
    def __init__(self):
        self.templates = {}
        self.channels = {}
        self.queues = {}
    
    async def send_notification(
        self,
        notification_type: str,
        recipients: List[str],
        data: dict,
        priority: str = "normal"
    ):
        """
        Send notification through user-preferred channels
        Handles template rendering and queuing
        """
    
    async def send_digest(
        self,
        workspace_id: str,
        digest_type: str,
        period: str
    ):
        """
        Send periodic digest notifications
        Aggregates events from specified period
        """
    
    async def get_user_preferences(
        self,
        user_id: str,
        workspace_id: str
    ):
        """
        Get user's notification preferences
        Returns channel settings and frequency
        """
    
    def render_template(
        self,
        template_name: str,
        data: dict,
        channel: str
    ):
        """
        Render notification template for specific channel
        Handles HTML, plain text, and markdown
        """
    
    async def track_delivery(
        self,
        notification_id: str,
        channel: str,
        status: str
    ):
        """
        Track notification delivery status
        Updates metrics and handles failures
        """
    
    async def manage_subscription(
        self,
        user_id: str,
        notification_type: str,
        action: str
    ):
        """
        Manage notification subscriptions
        Handle opt-in/opt-out preferences
        """

class NotificationChannelManager:
    async def send_in_app(
        self,
        user_id: str,
        notification: dict
    ):
        """Send in-app notification via WebSocket"""
    
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        html_body: str,
        text_body: str
    ):
        """Send email notification with fallback"""
    
    async def send_slack(
        self,
        webhook_url: str,
        message: dict
    ):
        """Send Slack notification with rich formatting"""
    
    async def send_teams(
        self,
        webhook_url: str,
        card: dict
    ):
        """Send Microsoft Teams adaptive card"""
    
    async def send_discord(
        self,
        webhook_url: str,
        embed: dict
    ):
        """Send Discord embed notification"""

#### Database Schema
```sql
-- Notification preferences
CREATE TABLE analytics.notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    frequency VARCHAR(20), -- 'immediate', 'hourly', 'daily', 'weekly'
    schedule_time TIME, -- For scheduled digests
    schedule_timezone VARCHAR(50),
    filter_rules JSONB, -- Custom filtering conditions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, workspace_id, notification_type, channel),
    INDEX idx_prefs_user (user_id, workspace_id)
);

-- Notification templates
CREATE TABLE analytics.notification_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) NOT NULL UNIQUE,
    notification_type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    subject_template TEXT,
    body_template TEXT NOT NULL,
    variables JSONB NOT NULL, -- Required variables
    preview_data JSONB, -- Sample data for preview
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(notification_type, channel),
    INDEX idx_templates_type (notification_type, channel)
);

-- Notification queue
CREATE TABLE analytics.notification_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_type VARCHAR(100) NOT NULL,
    recipient_id UUID NOT NULL,
    recipient_email VARCHAR(255),
    channel VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_for TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_attempt_at TIMESTAMP,
    delivered_at TIMESTAMP,
    failed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_queue_status (status, scheduled_for),
    INDEX idx_queue_recipient (recipient_id, status)
);

-- Notification history
CREATE TABLE analytics.notification_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_id UUID REFERENCES analytics.notification_queue(id),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    subject TEXT,
    preview TEXT,
    full_content TEXT,
    sent_at TIMESTAMP NOT NULL,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    clicked_at TIMESTAMP,
    delivery_status VARCHAR(20) NOT NULL,
    tracking_data JSONB,
    
    INDEX idx_log_user (user_id, sent_at DESC),
    INDEX idx_log_workspace (workspace_id, notification_type)
);

-- Digest aggregation
CREATE TABLE analytics.digest_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    digest_type VARCHAR(50) NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    events JSONB NOT NULL,
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    
    INDEX idx_digest_pending (is_sent, period_end),
    UNIQUE(user_id, workspace_id, digest_type, period_start)
);
```

### Frontend Components

#### Component: `components/analytics/NotificationCenter.tsx`
```typescript
interface NotificationCenterProps {
    userId: string;
    workspaceId: string;
}

export function NotificationCenter({
    userId,
    workspaceId
}: NotificationCenterProps) {
    // In-app notification feed
    // Notification preferences
    // Channel configuration
    // Digest settings
    
    return (
        <div className="notification-center">
            <NotificationFeed />
            <NotificationPreferences />
            <ChannelSettings />
            <DigestConfiguration />
            <NotificationHistory />
        </div>
    );
}

interface NotificationFeedProps {
    notifications: Notification[];
    onMarkRead: (id: string) => void;
    onDismiss: (id: string) => void;
}

export function NotificationFeed({
    notifications,
    onMarkRead,
    onDismiss
}: NotificationFeedProps) {
    // Real-time notification display
    // Grouped by type and time
    // Quick actions
    // Mark all as read
}

interface NotificationPreferencesProps {
    preferences: NotificationPreference[];
    onUpdate: (pref: NotificationPreference) => void;
}

export function NotificationPreferences({
    preferences,
    onUpdate
}: NotificationPreferencesProps) {
    // Toggle notifications by type
    // Set frequency preferences
    // Configure filters
    // Test notifications
}

interface DigestConfigurationProps {
    digestSettings: DigestSettings[];
    onUpdate: (settings: DigestSettings) => void;
}

export function DigestConfiguration({
    digestSettings,
    onUpdate
}: DigestConfigurationProps) {
    // Configure daily/weekly digests
    // Select included metrics
    // Set delivery time
    // Preview digest format
}
```

### API Endpoints

#### GET `/api/analytics/notifications`
- Query parameters: user_id, workspace_id, unread_only, limit
- Returns user's notifications
- Includes read status and actions

#### PUT `/api/analytics/notifications/{id}/read`
- Marks notification as read
- Updates read timestamp
- Returns updated notification

#### POST `/api/analytics/notifications/preferences`
- Updates notification preferences
- Request body: { notification_type, channel, enabled, frequency }
- Validates and saves preferences

#### POST `/api/analytics/notifications/test`
- Sends test notification
- Request body: { channel, template, sample_data }
- Useful for configuration testing

#### GET `/api/analytics/notifications/digest/preview`
- Preview digest content
- Query parameters: digest_type, period
- Returns formatted digest

#### POST `/api/analytics/notifications/bulk`
- Send bulk notifications
- Request body: { recipients, notification_type, data }
- Returns job ID for tracking

### Notification Types

1. **Alert Notifications**
   - Critical alerts
   - Warning alerts
   - Alert resolutions
   - Escalation notices

2. **Report Notifications**
   - Daily summaries
   - Weekly analytics
   - Monthly reports
   - Custom report completion

3. **Milestone Notifications**
   - Usage milestones
   - Growth achievements
   - Performance records
   - Goal completions

4. **System Notifications**
   - Maintenance windows
   - Feature updates
   - Policy changes
   - Security notices

### Template Examples

#### Email Template
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        .metric { font-size: 24px; font-weight: bold; }
        .change { color: {{ color }}; }
    </style>
</head>
<body>
    <h2>{{ workspace_name }} Daily Analytics</h2>
    <div class="metric">
        Active Users: {{ active_users }}
        <span class="change">{{ change_percent }}%</span>
    </div>
    <p>{{ summary_text }}</p>
    <a href="{{ dashboard_url }}">View Dashboard</a>
</body>
</html>
```

#### Slack Template
```json
{
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "{{ alert_title }}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Metric:*\n{{ metric_name }}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Value:*\n{{ metric_value }}"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details"
                    },
                    "url": "{{ detail_url }}"
                }
            ]
        }
    ]
}
```

## Implementation Priority
1. In-app notifications with WebSocket
2. Email notifications with templates
3. User preference management
4. Slack integration
5. Digest system

## Success Metrics
- Notification delivery rate > 99%
- Open rate > 40%
- Preference configuration time < 2 minutes
- Digest engagement rate > 30%