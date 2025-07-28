# Phase 1 Missing Services - Critical Implementation Gaps

## 1. Wikipedia Scraper Service
```typescript
// src/services/wikipedia.service.ts
interface WikipediaService {
  scrapeEvent(eventUrl: string): Promise<EventData>;
  scrapeFighter(fighterUrl: string): Promise<FighterData>;
  parseEventInfobox(html: string): EventInfobox;
  parseFighterNames(nameString: string): ParsedName;
}
```

## 2. Fighter Name Parser Service  
```typescript
// src/services/name-parser.service.ts
interface NameParserService {
  parseFullName(name: string): {
    first_name: string;
    last_name: string;
    display_name: string;
  };
  handleSingleName(name: string): ParsedName;
  detectNameVariations(names: string[]): NameVariation[];
}
```

## 3. Background Job Queue
```typescript
// src/services/queue.service.ts - Bull.js implementation
interface QueueService {
  addScrapingJob(type: 'event' | 'fighter', url: string): Promise<void>;
  addBulkImportJob(data: any[]): Promise<void>;
  processScheduledTasks(): Promise<void>;
}
```

## 4. Search Service
```typescript  
// src/services/search.service.ts
interface SearchService {
  searchFighters(query: string, options: SearchOptions): Promise<SearchResult[]>;
  fuzzyNameMatch(query: string): Promise<Fighter[]>;
  getAlphabeticalFighters(letter?: string): Promise<Fighter[]>;
}
```

## 5. API Routes (Currently Missing)
```typescript
// src/routes/ - All route files missing
- auth.routes.ts (authentication endpoints)
- fighter.routes.ts (fighter CRUD + search)  
- event.routes.ts (event CRUD + fight data)
- content.routes.ts (news/blog management)
- admin.routes.ts (admin operations)
```

## 6. Repository Pattern Implementation
```typescript
// src/repositories/ - Data access layer missing
- fighter.repository.ts
- event.repository.ts  
- fight.repository.ts
- content.repository.ts
```

## 7. Validation Schemas
```typescript
// src/validators/ - Request validation missing
- fighter.validator.ts
- event.validator.ts
- auth.validator.ts
```

## Implementation Priority
1. **HIGH**: Wikipedia scraper + name parser (core data)
2. **HIGH**: Fighter/Event repositories + routes
3. **MEDIUM**: Background job processing
4. **MEDIUM**: Search functionality  
5. **LOW**: Admin routes + advanced features