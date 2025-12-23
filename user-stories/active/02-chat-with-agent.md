# User Story 2: Chat with Profile Agent

## User Story

**As a** White Rabbit member
**I want to** have a conversation with the AI agent
**So that** I can discuss what to add to my profile in a natural, conversational way

## Description

Members should be able to have a natural conversation with the Profile Optimizer agent about their profile. The agent asks thoughtful questions, listens to responses, and helps members articulate what they want on their profile - without automatically publishing anything.

## Acceptance Criteria

### Given a member opens the Profile Optimizer chat
- [x] When they start a conversation
- [x] Then the agent greets them warmly
- [x] And the agent references their current profile completeness score
- [x] And the agent asks if they'd like help with specific missing fields

### Given a member is chatting with the agent
- [x] When they send a message
- [x] Then they receive a contextual response within 3 seconds
- [x] And the conversation history is preserved during the session
- [x] And the agent remembers previous context in the conversation

### Given a member provides information in conversation
- [x] When they share details about their work, interests, or goals
- [x] Then the agent acknowledges and asks clarifying questions
- [x] And the conversation stays private (not auto-published to profile)
- [x] And the agent can reference this information in future responses

### Given a member wants to end the conversation
- [x] When they close the chat or navigate away
- [x] Then their conversation history is saved
- [ ] And they can resume the conversation later (if session management exists)

## Technical Notes

### AI Agent Behavior
- **Tone:** Friendly, professional, curious
- **Goal:** Help member articulate profile content, not interrogate
- **Approach:** Ask open-ended questions, listen, clarify
- **Boundaries:** Don't push if member is hesitant, respect pace

### Conversation Context
- Member's current profile data
- Profile completeness score
- Previous messages in current session
- (Future: Previous conversation sessions)

### API Endpoints
```
POST /api/v1/chat
Request: {
  "message": "I'm a software developer",
  "session_id": "uuid-here"
}
Response: {
  "response": "That's great! What kind of software do you enjoy building?",
  "session_id": "uuid-here"
}

GET /api/v1/chat/history?session_id=uuid
Response: {
  "messages": [
    {"role": "assistant", "content": "Hi! I see your profile is 65% complete..."},
    {"role": "user", "content": "I'd like to add more about my work"},
    {"role": "assistant", "content": "I'd love to help with that..."}
  ]
}
```

### Data Storage
- `conversation_history` table stores all messages
- `session_id` groups messages together
- Messages are append-only (never deleted/edited)
- Member can review full conversation history

## Ethical Considerations

- ✅ **Consent:** Member initiates conversation
- ✅ **Privacy:** Conversation is private, not public profile
- ✅ **Control:** Member can stop at any time
- ✅ **Transparency:** Clear that AI is generating responses
- ✅ **No auto-publish:** Nothing goes to profile without explicit approval (Story 3)

## Example Conversation Flow

```
Assistant: Hi! I see your profile is 65% complete. You're missing info about
           your website and current focus. Would you like help filling those in?

Member: Sure, I'd like to add what I'm working on

Assistant: Great\! Tell me about what you're currently working on.

Member: I'm building web apps with Python and React. Most of my recent work
        has been focused on tools for the local creative community.

Assistant: That sounds wonderful\! What draws you to that particular focus?

Member: I really believe in helping local creators succeed with technology.

Assistant: I love that mission. And what kind of website do you have for your work?

Member: I have a portfolio at example.com

[Conversation continues... agent gathers context without publishing anything]
```

## Implementation Order

1. [x] Backend: Chat endpoint with Claude API integration
2. [x] Backend: Conversation history storage
3. [x] Backend: Session management
4. [x] Frontend: Chat UI component
5. [x] Frontend: Message display and input
6. [x] Integration: Real-time conversation with context preservation

## Out of Scope

- ❌ Publishing content to profile (that's Story 3)
- ❌ Multi-session conversation memory (future enhancement)
- ❌ Social media profile fetching (separate feature)
- ❌ Voice/audio conversation interface
- ❌ File uploads or attachments

## Success Metrics

- Response time under 3 seconds
- Conversation context preserved throughout session
- Agent tone feels helpful, not interrogating
- Member feels comfortable sharing information
- Clear distinction between private chat and public profile
