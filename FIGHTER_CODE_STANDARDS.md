# Fighter Profile Management - Code Quality Standards

## Architecture Principles

### 1. Model Design Standards
- **Structured Names**: Always use `first_name` and `last_name` fields separately
- **Computed Properties**: Use `@property` for calculated fields like `get_full_name()`
- **Data Quality**: Maintain `data_quality_score` field for completeness tracking
- **Validation**: Use Django model validators and clean() methods
- **Indexes**: Ensure proper database indexes for search fields

### 2. API Design Standards
- **ViewSet Structure**: Use ModelViewSet with action-specific serializers
- **Search Strategy**: Implement multi-tier search (exact → variation → fulltext → fuzzy)
- **Performance**: Always use `select_related()` and `prefetch_related()`
- **Pagination**: Implement pagination for all list endpoints
- **Error Handling**: Return structured error responses with appropriate HTTP codes

### 3. Admin Interface Standards
- **Fieldsets**: Organize fields logically (Basic → Personal → Physical → Career)
- **List Display**: Show key identifying information (name, record, nationality)
- **Search Fields**: Include all name-related fields for search
- **Actions**: Provide bulk operations for common admin tasks
- **Inlines**: Use inlines for related models (name variations)

### 4. Search Implementation Standards
- **Strategy Hierarchy**: Exact → Variation → Partial → Fulltext → Fuzzy
- **Performance Limits**: Cap results per strategy to prevent overload
- **Metadata**: Return match type and confidence scores
- **Query Optimization**: Use proper database indexes and query optimization
- **Caching**: Consider Redis caching for frequent searches

### 5. Data Validation Standards
- **Name Validation**: Ensure first_name is never empty
- **Physical Attributes**: Validate reasonable ranges (height: 120-250cm, weight: 40-200kg)
- **Record Consistency**: Ensure wins + losses + draws = total_fights
- **Data Source Tracking**: Always track data_source and update timestamps

### 6. Testing Standards
- **Model Tests**: Test all computed properties and validation
- **API Tests**: Test all endpoints with various scenarios
- **Search Tests**: Test all search strategies with edge cases
- **Admin Tests**: Test admin actions and form validation
- **Performance Tests**: Test search performance with large datasets

## Code Examples

### Model Property Example
```python
@property
def full_name(self):
    """Computed full name property"""
    if self.last_name:
        return f"{self.first_name} {self.last_name}"
    return self.first_name

def get_record_string(self):
    """Format fight record as string"""
    record = f"{self.wins}-{self.losses}-{self.draws}"
    if self.no_contests > 0:
        record += f" ({self.no_contests} NC)"
    return record
```

### Search Implementation Example
```python
# Multi-strategy search with performance optimization
exact_matches = fighters.filter(
    Q(first_name__iexact=query) |
    Q(last_name__iexact=query) |
    Q(nickname__iexact=query)
).select_related().prefetch_related('name_variations')
```

### Admin Action Example
```python
def update_data_quality(self, request, queryset):
    """Bulk update data quality scores"""
    for fighter in queryset:
        fighter.data_quality_score = self.calculate_data_quality(fighter)
        fighter.save()
    self.message_user(request, f"Updated {queryset.count()} fighters")
```

## Performance Guidelines

### Database Optimization
- Use `select_related()` for ForeignKey relationships
- Use `prefetch_related()` for ManyToMany and reverse ForeignKey
- Create proper indexes for search fields
- Use database-level constraints where possible

### Search Optimization
- Implement search result caching for common queries
- Limit results per search strategy to prevent overload
- Use PostgreSQL full-text search for complex queries
- Consider search result ranking and relevance scoring

### API Performance
- Implement proper pagination for all list endpoints
- Use lightweight serializers for list views
- Cache frequently accessed data (active fighters, etc.)
- Monitor and optimize slow queries

## Security Considerations

### Input Validation
- Sanitize all user inputs in serializers
- Validate name formats and character sets
- Prevent SQL injection through proper ORM usage
- Validate file uploads (profile images)

### Data Access
- Implement proper authentication and authorization
- Use Django permissions for admin access
- Log all data modifications for audit trails
- Secure sensitive data (birthdates, personal info)

## Documentation Standards

### Code Documentation
- Document all model methods and properties
- Provide clear docstrings for ViewSet actions
- Comment complex search algorithms
- Document admin customizations

### API Documentation
- Use DRF Spectacular for automatic documentation
- Provide clear examples for all endpoints
- Document search parameters and response formats
- Include error response examples

## Deployment Considerations

### Database
- Ensure proper migration order for indexes
- Monitor query performance in production
- Set up database connection pooling
- Configure proper backup strategies

### Caching
- Implement Redis caching for search results
- Cache frequently accessed fighter profiles
- Set appropriate cache TTL values
- Monitor cache hit rates

### Monitoring
- Track search performance metrics
- Monitor API response times
- Set up alerts for data quality issues
- Log search patterns for optimization