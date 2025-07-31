# Wikipedia Scraper Timeout Debugging & Solutions

## Problem Identified
The UFC Wikipedia scraper was experiencing timeout issues when trying to fetch data from Wikipedia. The original implementation had no timeout handling and poor error categorization.

## Root Cause Analysis

### 1. Diagnostic Results
- ✅ Basic Wikipedia connectivity: Working (0.2-0.3s response times)
- ✅ UFC 300 page fetch: Working (243KB content loaded successfully)
- ✅ HTML parsing speed: Fast (0.07s for BeautifulSoup parsing)
- ❌ **Missing timeout configuration**: No timeout set on HTTP requests
- ❌ **Poor error handling**: Generic RequestException catching

### 2. Issues Found
1. **No request timeouts**: HTTP requests could hang indefinitely
2. **No retry mechanism**: Single failure would cause complete failure
3. **Poor error categorization**: All errors treated the same way
4. **No circuit breaker**: Repeated failures would continue indefinitely
5. **Limited debugging info**: Hard to diagnose specific failure types

## Solutions Implemented

### 1. Added Comprehensive Timeout Handling

```python
class WikipediaGeminiScraper:
    def __init__(self, rate_limit_delay: float = 1.0, request_timeout: int = 30):
        self.request_timeout = request_timeout
        # Configure session with timeout and retry settings
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
```

### 2. Enhanced Error Handling

```python
except requests.exceptions.Timeout as e:
    logger.error(f"Timeout error scraping {event_url} after {self.request_timeout}s: {e}")
except requests.exceptions.ConnectionError as e:
    logger.error(f"Connection error scraping {event_url}: {e}")
except requests.exceptions.HTTPError as e:
    logger.error(f"HTTP error scraping {event_url}: {e}")
```

### 3. Circuit Breaker Implementation

```python
# Track consecutive failures for circuit breaking
self.consecutive_failures = 0
self.max_consecutive_failures = 3

# Check circuit breaker before each request
if self.consecutive_failures >= self.max_consecutive_failures:
    logger.error(f"Circuit breaker triggered after {self.consecutive_failures} failures")
    # Return error result instead of attempting request
```

### 4. Connectivity Testing

```python
def test_connectivity(self) -> Tuple[bool, str]:
    """Test connectivity to Wikipedia"""
    try:
        response = self.session.get("https://en.wikipedia.org", timeout=10)
        response.raise_for_status()
        return True, f"✅ Wikipedia connectivity OK ({elapsed:.2f}s)"
    except requests.exceptions.Timeout:
        return False, "❌ Wikipedia connectivity timeout"
```

### 5. Better Debugging and Monitoring

- Added detailed logging for each request phase
- Response size logging to identify large pages
- Circuit breaker status tracking
- Retry attempt logging
- Performance timing for each operation

## Testing Tools Created

### 1. Diagnostic Script (`test_wikipedia_timeout.py`)
- Tests basic connectivity
- Tests UFC 300 page specifically  
- Tests different timeout values
- Tests session configuration
- Tests HTML parsing speed

### 2. Improved Scraper Test (`test_improved_scraper.py`)
- Tests different timeout configurations
- Tests circuit breaker functionality
- Provides detailed performance metrics

### 3. Django Management Command (`test_wikipedia_scraper`)
```bash
python manage.py test_wikipedia_scraper --test-connectivity --url https://en.wikipedia.org/wiki/UFC_300 --timeout 15
```

## Performance Results

### Before Improvements
- ❌ Requests could timeout after 2+ minutes
- ❌ No error categorization
- ❌ No retry mechanism
- ❌ No failure prevention

### After Improvements
- ✅ Configurable timeouts (default 30s)
- ✅ 3 automatic retries with backoff
- ✅ Circuit breaker prevents cascade failures
- ✅ Detailed error categorization
- ✅ Connectivity pre-testing
- ✅ Performance monitoring

### Test Results
```
✅ UFC 300 scraping: 0.64s (successful)
✅ Circuit breaker: Triggers after 3 failures
✅ Connectivity test: 0.24s response time
✅ All sections extracted: first_paragraph, infobox, results_table
```

## Configuration Recommendations

### Production Settings
```python
scraper = WikipediaGeminiScraper(
    rate_limit_delay=1.0,      # 1 second between requests
    request_timeout=30         # 30 second timeout
)
```

### Development/Testing Settings
```python
scraper = WikipediaGeminiScraper(
    rate_limit_delay=0.5,      # Faster for testing
    request_timeout=15         # Shorter timeout for quick feedback
)
```

### High-Volume Settings
```python
scraper = WikipediaGeminiScraper(
    rate_limit_delay=2.0,      # Respectful rate limiting
    request_timeout=60         # Longer timeout for large pages
)
```

## Usage Examples

### Basic Usage
```python
scraper = WikipediaGeminiScraper()

# Test connectivity first
success, message = scraper.test_connectivity()
if success:
    result = scraper.scrape_event_page("https://en.wikipedia.org/wiki/UFC_300")
```

### With Error Handling
```python
scraper = WikipediaGeminiScraper(request_timeout=30)

try:
    result = scraper.scrape_event_page(url)
    if result.extraction_success:
        # Process successful result
        pass
    else:
        # Handle partial failure
        logger.warning(f"Partial extraction: {result.error_messages}")
except Exception as e:
    # Handle complete failure
    logger.error(f"Scraping failed: {e}")
```

### Circuit Breaker Management
```python
# Check circuit breaker status
status = scraper.get_circuit_breaker_status()
if status['is_open']:
    logger.warning("Circuit breaker is open, resetting...")
    scraper.reset_circuit_breaker()
```

## Monitoring and Debugging Commands

### Test specific events
```bash
python manage.py test_wikipedia_scraper --url https://en.wikipedia.org/wiki/UFC_299 --timeout 20
```

### Test connectivity only
```bash
python manage.py test_wikipedia_scraper --test-connectivity
```

### Show extracted HTML (debugging)
```bash  
python manage.py test_wikipedia_scraper --show-html --url https://en.wikipedia.org/wiki/UFC_300
```

## Summary

The timeout issues were resolved by implementing comprehensive timeout handling, retry mechanisms, circuit breaker patterns, and better error categorization. The scraper now performs reliably with proper error handling and monitoring capabilities.

**Key improvements:**
- 🚀 **30s default timeout** instead of indefinite waiting
- 🔄 **3 automatic retries** with exponential backoff  
- 🔒 **Circuit breaker** prevents cascade failures
- 📊 **Detailed error categorization** for better debugging
- 🧪 **Comprehensive testing tools** for ongoing monitoring
- ⚡ **Performance optimizations** with session reuse and proper headers