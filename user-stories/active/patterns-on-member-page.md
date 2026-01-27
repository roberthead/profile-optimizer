# Patterns on Member Page

AS a user
ON a member page (/members/[:id])
I WANT to see a list of patterns that this member matches

## Acceptance Criteria

- Patterns section appears below Profile Responses section
- Each pattern displays as a compact badge: name + category indicator
- Clicking a pattern navigates to the /patterns page
- Section only appears if the member has matching patterns

## Implementation Plan

### 1. Frontend: Add patterns fetch to MemberDetail.tsx

Add a query to fetch all active patterns:

```typescript
const { data: patterns } = useQuery({
  queryKey: ['patterns'],
  queryFn: fetchPatterns,
});
```

### 2. Frontend: Filter patterns for current member

Filter patterns where `related_member_ids` includes the member's ID:

```typescript
const memberPatterns = patterns?.filter(
  (pattern) => pattern.related_member_ids.includes(member.id)
) ?? [];
```

### 3. Frontend: Add Patterns section component

Create a new section below Profile Responses displaying:
- Section header with Sparkles icon: "Community Patterns"
- Horizontal flex-wrap of pattern badges
- Each badge shows: category icon + pattern name
- Badge uses category color scheme (reuse from Patterns.tsx)
- Entire badge is a Link to `/patterns`

### 4. UI Details

- Reuse `categoryColors`, `categoryLabels`, `categoryIcons` from Patterns.tsx (consider extracting to shared constants)
- Badge styling similar to skills/interests badges but with category-specific colors
- If no patterns match, section is hidden (not shown empty)

### Files to Modify

- `frontend/src/pages/MemberDetail.tsx` - Add patterns query, filter logic, and new section
