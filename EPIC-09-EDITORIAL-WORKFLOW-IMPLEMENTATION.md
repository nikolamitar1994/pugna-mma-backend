# EPIC-09 Editorial Workflow and Permissions Implementation

## Overview

This document summarizes the comprehensive editorial workflow and permissions system implemented for the MMA Database content management system. The implementation provides a complete role-based editorial workflow with proper permissions, status transitions, notifications, and audit trails.

## 🎯 Features Implemented

### 1. **User Roles & Permissions**

**Four distinct editorial roles with hierarchical permissions:**

- **Author**: Can create and edit their own articles (draft status only)
- **Editor**: Can review, edit, and approve articles for publishing  
- **Publisher**: Can publish, feature, archive articles, and manage categories/tags
- **Admin**: Full content management access with system administration

**Custom permissions created:**
- `can_create_article` - Create new articles
- `can_edit_own_articles` - Edit own articles
- `can_edit_any_article` - Edit any article
- `can_publish_article` - Publish articles
- `can_archive_article` - Archive articles
- `can_feature_article` - Mark articles as featured
- `can_set_breaking_news` - Mark articles as breaking news
- `can_assign_editor` - Assign editors to articles
- `can_view_unpublished` - View unpublished content
- `can_view_analytics` - Access analytics data
- `can_manage_categories` - Manage content categories
- `can_manage_tags` - Manage content tags
- `can_approve_articles` - Approve articles for publishing
- `can_reject_articles` - Reject articles
- `can_view_workflow_logs` - View editorial workflow logs
- And more...

### 2. **Editorial Workflow States**

**Four workflow states with controlled transitions:**

- **Draft**: Author can edit, not visible to public
- **Under Review**: Submitted for editorial review, author cannot edit
- **Published**: Live on site, public can view
- **Archived**: Not visible to public but preserved

**Valid state transitions:**
- Draft → Review, Published, Archived
- Review → Draft, Published, Archived  
- Published → Archived
- Archived → Draft, Review

### 3. **Models & Database Schema**

**Enhanced User Model (`users/models.py`):**
```python
class User(AbstractUser):
    # Extended fields for editorial workflow
    bio = models.TextField(blank=True)
    email_notifications = models.BooleanField(default=True)
    
    def get_editorial_role(self):
        # Returns highest editorial role
    
    def can_edit_article(self, article):
        # Role-based article editing permissions
    
    def can_publish_article(self, article):
        # Publishing permission check
```

**User Profile Model:**
```python
class UserProfile(models.Model):
    editorial_role = models.CharField(choices=EDITORIAL_ROLES)
    articles_authored = models.PositiveIntegerField(default=0)
    articles_published = models.PositiveIntegerField(default=0)
    # Activity tracking and notification preferences
```

**Editorial Workflow Log:**
```python
class EditorialWorkflowLog(models.Model):
    article = models.ForeignKey(Article)
    user = models.ForeignKey(User)
    action = models.CharField(choices=ACTION_TYPES)
    from_status = models.CharField()
    to_status = models.CharField()
    notes = models.TextField()
    metadata = models.JSONField()
```

**Assignment Notifications:**
```python
class AssignmentNotification(models.Model):
    recipient = models.ForeignKey(User)
    article = models.ForeignKey(Article)
    notification_type = models.CharField(choices=NOTIFICATION_TYPES)
    title = models.CharField()
    message = models.TextField()
    email_sent = models.BooleanField(default=False)
```

### 4. **Services & Business Logic**

**Editorial Workflow Service (`content/services.py`):**
- `EditorialWorkflowService`: Manages status transitions with validation
- `NotificationService`: Handles email notifications for workflow changes
- `RoleManagementService`: Manages role assignments and permissions
- `ContentAnalyticsService`: Provides productivity and performance analytics

**Key service methods:**
```python
def transition_article_status(article, new_status, user, notes=''):
    # Validates transition and logs action
    
def submit_for_review(article, user, notes=''):
    # Submits article for editorial review
    
def approve_article(article, user, notes=''):
    # Approves and publishes article
    
def assign_editor(article, editor, assigner, notes=''):
    # Assigns editor with notification
```

### 5. **API Integration with Role-Based Permissions**

**Permission Classes (`content/permissions.py`):**
- `EditorialWorkflowPermission`: Comprehensive workflow permissions
- `CanEditArticle`: Article-specific edit permissions
- `CanPublishArticle`: Publishing permissions
- `CanManageCategories`: Category management permissions

**ViewSet Mixins (`content/mixins.py`):**
- `EditorialWorkflowMixin`: Adds workflow actions to ViewSets
- `BulkActionsMixin`: Bulk publish/archive operations
- `ContentAnalyticsMixin`: Analytics endpoints
- `AuthorArticlesMixin`: Author-specific filtering
- `StatusFilterMixin`: Status-based filtering

**New API Endpoints:**
```
POST /api/v1/articles/{id}/submit_for_review/
POST /api/v1/articles/{id}/publish/
POST /api/v1/articles/{id}/archive/
POST /api/v1/articles/{id}/approve/
POST /api/v1/articles/{id}/reject/
POST /api/v1/articles/{id}/assign_editor/
GET  /api/v1/articles/{id}/workflow_logs/
POST /api/v1/articles/bulk_publish/
POST /api/v1/articles/bulk_archive/
GET  /api/v1/articles/my_articles/
GET  /api/v1/articles/assigned_to_me/
GET  /api/v1/articles/under_review/
GET  /api/v1/articles/my_analytics/
```

### 6. **Role-Based Serializers**

**Dynamic Field Serializers (`content/serializers.py`):**
- `EditorialArticleListSerializer`: Role-based field visibility
- `EditorialArticleDetailSerializer`: Comprehensive editorial info
- `EditorialArticleCreateUpdateSerializer`: Role-based validation

**Permission-aware fields:**
- Authors see basic fields + own article actions
- Editors see review fields + workflow actions
- Publishers see all fields + admin actions
- Different serializer fields based on user role

### 7. **Enhanced Django Admin**

**Permission-based Admin Interface:**
- Articles filtered by user permissions
- Readonly fields based on role and article status
- Custom admin actions with workflow logging
- Workflow log viewing with audit trail
- User profile management with activity stats

**Admin features:**
- Authors only see own articles
- Editors see articles in review + own articles
- Publishers/Admins see all articles
- Workflow actions with proper permission checks
- Bulk operations with workflow logging

### 8. **Management Commands**

**Setup and User Management:**
```bash
# Setup editorial roles and permissions
python manage.py setup_editorial_roles

# Assign role to existing user
python manage.py assign_editorial_role john.doe editor

# Create new user with role
python manage.py create_editorial_user --username editor1 --role editor

# List users and roles
python manage.py assign_editorial_role --list-users
```

### 9. **Email Notification System**

**Automated Notifications:**
- Editor assignment notifications
- Status change notifications (published, rejected, etc.)
- Configurable per-user notification preferences
- Email templates with article context
- Notification tracking and read status

**Notification triggers:**
- Article submitted for review
- Article approved/published
- Article rejected with notes
- Editor assigned to article
- Status changes by other users

### 10. **Audit Trail & Analytics**

**Complete Audit Trail:**
- All workflow actions logged with user, timestamp, notes
- Article edit history tracking
- Status transition logging with before/after states
- User activity statistics

**Analytics Features:**
- User productivity statistics (articles created, published)
- Content performance metrics (views, engagement)
- Workflow statistics (articles in each status)
- Editorial team activity tracking

## 🔧 Implementation Files

### Core Files Created/Modified:

1. **`users/models.py`** - Extended User model with editorial roles
2. **`content/permissions.py`** - Custom permissions and permission classes
3. **`content/services.py`** - Editorial workflow business logic
4. **`content/mixins.py`** - ViewSet mixins for workflow actions
5. **`content/serializers.py`** - Role-based serializers
6. **`content/admin.py`** - Enhanced admin with permissions
7. **`api/views.py`** - Updated ArticleViewSet with workflow features

### Management Commands:
8. **`content/management/commands/setup_editorial_roles.py`**
9. **`content/management/commands/assign_editorial_role.py`**
10. **`content/management/commands/create_editorial_user.py`**

## 🚀 Usage Examples

### Setting up the system:
```bash
# 1. Setup roles and permissions
python manage.py setup_editorial_roles

# 2. Create editorial users
python manage.py create_editorial_user --username author1 --role author
python manage.py create_editorial_user --username editor1 --role editor
python manage.py create_editorial_user --username publisher1 --role publisher

# 3. Assign roles to existing users
python manage.py assign_editorial_role existing.user@email.com editor
```

### API Usage:
```python
# Create article (Author)
POST /api/v1/articles/
{
    "title": "New MMA News",
    "content": "Article content...",
    "status": "draft"
}

# Submit for review (Author)
POST /api/v1/articles/{id}/submit_for_review/
{
    "notes": "Ready for review"
}

# Approve article (Editor)
POST /api/v1/articles/{id}/approve/
{
    "notes": "Looks good, publishing now"
}

# Assign editor (Publisher/Admin)
POST /api/v1/articles/{id}/assign_editor/
{
    "editor_id": "uuid-here",
    "notes": "Please review this article"
}
```

### Admin Interface:
- Authors: See only their own articles, can edit drafts
- Editors: See articles under review + own articles, can approve/reject
- Publishers: See all articles, can publish/feature/archive
- Admins: Full access to all features and settings

## 🔒 Security Features

- **Permission-based access**: Every action requires appropriate permissions
- **Status-based editing**: Users can only edit articles in allowed states
- **Audit logging**: All actions tracked with user attribution
- **Input validation**: Role-based field validation in serializers
- **Admin protection**: Sensitive admin actions require higher permissions

## 📊 Benefits

1. **Clear Role Separation**: Each role has specific responsibilities and limitations
2. **Workflow Enforcement**: Proper editorial process with status tracking
3. **Audit Compliance**: Complete audit trail of all editorial actions
4. **User Experience**: Role-appropriate interfaces and available actions
5. **Scalability**: Easy to add new roles or modify permissions
6. **Integration**: Seamless integration with existing Django admin and DRF APIs
7. **Notifications**: Automated notifications keep team informed
8. **Analytics**: Insights into editorial team productivity and content performance

## 🎉 Result

The implementation provides a complete, production-ready editorial workflow system with:

- ✅ **4 distinct user roles** with hierarchical permissions
- ✅ **4 workflow states** with controlled transitions  
- ✅ **Complete audit trail** with workflow logging
- ✅ **Email notification system** for workflow changes
- ✅ **Role-based API endpoints** with proper permissions
- ✅ **Dynamic serializers** showing appropriate fields per role
- ✅ **Enhanced Django admin** with permission-based interfaces
- ✅ **Management commands** for easy setup and user management
- ✅ **Analytics and reporting** for editorial team insights

The system is ready for immediate use and can handle complex editorial workflows while maintaining security, auditability, and user experience.