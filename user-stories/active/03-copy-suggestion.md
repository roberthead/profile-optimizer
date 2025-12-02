# User Story 3: Copy Suggestion to Profile

## User Story

**As a** White Rabbit member
**I want to** review and approve AI-suggested profile content
**So that** I can publish the information I'm comfortable sharing

## Description

After having a conversation with the agent, members can review AI-generated suggestions for their profile fields. The member always has final approval - they can accept, edit, or reject any suggested content before it becomes part of their public profile.

## Acceptance Criteria

### Given a member has discussed profile content with the agent
- [ ] When the conversation reaches a natural pause
- [ ] Then the agent offers to draft suggested profile content
- [ ] And the member can choose to see suggestions or continue chatting

### Given the agent generates profile suggestions
- [ ] When the member views the suggestions
- [ ] Then they see a clear preview of proposed changes
- [ ] And they see which fields will be updated
- [ ] And they can see before/after comparison for existing fields
- [ ] And the suggestions are clearly marked as drafts (not published)

### Given a member reviews a suggestion
- [ ] When they decide on the suggestion
- [ ] Then they can accept it as-is
- [ ] Or they can edit the text before publishing
- [ ] Or they can reject it entirely
- [ ] And accepting publishes ONLY that specific field
- [ ] And they can accept/reject suggestions independently (not all-or-nothing)

### Given a member accepts a suggestion
- [ ] When they click "Publish to Profile"
- [ ] Then the content is written to their profile in the database
- [ ] And they see confirmation that the update succeeded
- [ ] And their profile completeness score updates if applicable
- [ ] And the change is immediately visible on their public profile

### Given a member edits a suggestion
- [ ] When they modify the AI-generated text
- [ ] Then their edits are preserved
- [ ] And they can preview the edited version
- [ ] And they explicitly publish when ready

## Technical Notes

### Suggestion Generation
- AI generates suggestions based on conversation context
- Each suggestion maps to a specific profile field
- Suggestions include reasoning/source (e.g., "Based on your mention of...")
- Multiple suggestions can be generated at once

### API Endpoints
```
POST /api/v1/suggestions/generate
Request: {
  "session_id": "uuid-here",
  "member_id": "member-uuid"
}
Response: {
  "suggestions": [
    {
      "id": "suggestion-uuid-1",
      "field": "current_focus",
      "current_value": "",
      "suggested_value": "Building web apps with Python and React",
      "reasoning": "Based on your conversation about recent projects",
      "confidence": "high"
    },
    {
      "id": "suggestion-uuid-2",
      "field": "website",
      "current_value": null,
      "suggested_value": "https://example.com",
      "reasoning": "You mentioned your portfolio site",
      "confidence": "medium"
    }
  ]
}

POST /api/v1/suggestions/:id/accept
Request: {
  "edited_value": "Building web apps with Python and React" // optional
}
Response: {
  "success": true,
  "updated_field": "current_focus",
  "new_value": "Building web apps with Python and React"
}

POST /api/v1/suggestions/:id/reject
Response: {
  "success": true
}
```

### Data Storage
- `profile_suggestions` table stores generated suggestions
- Tracks status: pending, accepted, edited, rejected
- Records what was suggested vs what was actually published
- Audit trail for transparency

### Profile Update Flow
1. Agent conversation → context gathering
2. Generate suggestions → store in `profile_suggestions`
3. Member reviews → UI shows before/after
4. Member accepts/edits → update `members` table
5. Confirmation → show updated profile + new completeness score

## Ethical Considerations

- ✅ **Human in the loop:** AI suggests, human approves
- ✅ **No surprises:** Clear preview before publishing
- ✅ **Granular control:** Accept/reject individual fields
- ✅ **Edit freedom:** Can modify AI suggestions
- ✅ **Transparency:** Shows reasoning for suggestions
- ✅ **Reversible:** Member can edit their profile later (not in this story, but system allows)
- ✅ **Audit trail:** System records what was suggested vs accepted

## Example Suggestion Flow

```
[After conversation about member's work and interests]
Assistant: It sounds like you've had some great conversations! Based on what
           you shared, I'd like to suggest some updates to your profile.
           Would you like to see my suggestions?

Member: Yes, show me

[UI shows suggestion cards]

---
Suggestion 1: Current Focus
Field: current_focus
Current: (empty)
Suggested: "Building web apps with Python and React, with a focus on
            community-driven projects that support local creators"
Reasoning: Based on your conversation about recent projects and passion
           for supporting the local community

[Accept] [Edit] [Reject]
---

Member: [Clicks Edit on Suggestion 1]
Member: [Changes text to "Building web apps that support local creators"]
Member: [Clicks "Publish to Profile"]

Confirmation: ✅ Your "Current Focus" has been updated!
Profile completeness: 65% → 75%
```

## Implementation Order

1. Backend: Suggestion generation logic using Claude API
2. Backend: API endpoints for generate/accept/reject
3. Backend: Database schema for `profile_suggestions` table
4. Frontend: Suggestion review UI component
5. Frontend: Before/after preview display
6. Frontend: Edit capability for suggestions
7. Integration: Accept flow updates member profile and completeness score

## Out of Scope

- ❌ Batch accept/reject (each suggestion handled individually)
- ❌ Auto-accepting suggestions (human always approves)
- ❌ Suggesting content without prior conversation context
- ❌ Editing published profile content (separate feature for profile management)
- ❌ Version history of profile changes (future enhancement)

## Success Metrics

- Member can review suggestions clearly
- Accept/reject/edit flow is intuitive
- No suggestions auto-publish without explicit approval
- Profile updates reflect immediately after acceptance
- Member feels in control of their profile content
