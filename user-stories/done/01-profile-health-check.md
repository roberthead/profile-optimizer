# User Story 1: Profile Health Check

## User Story

**As a** White Rabbit member
**I want to** see my profile completeness score
**So that** I know what information is missing from my profile

## Description

The first interaction with the Profile Optimizer should give members a clear understanding of their current profile state. This non-invasive, read-only feature builds trust and provides immediate value without requiring any conversation or data entry.

## Acceptance Criteria

### Given a member has an existing White Rabbit profile
- [x] When they visit the Profile Optimizer
- [x] Then they see a "Profile Health" score (0-100%)
- [x] And they see a visual indicator (progress bar or similar)
- [x] And they see a list of missing or incomplete fields

### Given a member's profile is incomplete
- [x] When they view their profile health
- [x] Then missing fields are clearly identified
- [x] And optional vs required fields are distinguished
- [x] And the completeness percentage reflects actual gaps

### Given a member's profile is 100% complete
- [x] When they view their profile health
- [x] Then they see a success message
- [x] And they're encouraged to keep it up-to-date

## Technical Notes

### Profile Fields to Evaluate
- Basic info: first name, last name, email (required)
- Professional: what you do, location, website
- Interests and skills (if schema supports)
- Profile photo
- Current focus / availability

### Completeness Calculation
- Simple percentage: (fields_filled / total_fields) * 100
- Weight optional fields less than required fields (if applicable)
- Store calculation results in `profile_completeness` table

### API Endpoint
```
POST /api/v1/profile/evaluate
Response: {
  "completeness_score": 65,
  "missing_fields": ["website", "current_focus", "interests"],
  "optional_missing": ["profile_photo"],
  "last_calculated": "2024-12-01T18:00:00Z"
}
```

## Ethical Considerations

- ✅ Read-only operation - no data modification
- ✅ No AI conversation required - simple calculation
- ✅ Transparent - clearly shows what's being evaluated
- ✅ No external data sources - only member's own profile

## Implementation Order

1. [x] Backend: Profile evaluation logic (`agents/profile_evaluation.py`)
2. [x] Backend: API endpoint for evaluation
3. [x] Frontend: Profile Health component with progress bar
4. [x] Frontend: Missing fields list display

## Out of Scope

- ❌ AI-generated suggestions (that's Story 2)
- ❌ Automatic profile updates
- ❌ Social media scraping
- ❌ Recommendations on how to improve

## Success Metrics

- Member can see their score within 2 seconds
- Score accurately reflects profile state
- Missing fields are clearly actionable
