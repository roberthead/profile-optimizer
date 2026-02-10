"""Tools for LLM agents to interact with community data."""

from app.tools.graph_tools import (
    get_all_members_with_profiles,
    get_existing_edges,
    get_active_patterns,
    save_edge,
    GET_ALL_MEMBERS_TOOL,
    GET_EXISTING_EDGES_TOOL,
    GET_ACTIVE_PATTERNS_TOOL,
    SAVE_EDGE_TOOL,
)

from app.tools.question_tools import (
    get_community_profile_analysis,
    get_member_gaps,
    save_pattern,
    GET_COMMUNITY_ANALYSIS_TOOL,
    GET_MEMBER_GAPS_TOOL,
    SAVE_QUESTION_DECK_TOOL,
    GET_ACTIVE_PATTERNS_TOOL as GET_PATTERNS_TOOL,
    SAVE_PATTERN_TOOL,
)

from app.tools.event_tools import (
    get_member_event_signals,
    record_event_signal,
    get_upcoming_events,
    compute_taste_affinity_scores,
    GET_EVENT_SIGNALS_TOOL,
    RECORD_EVENT_SIGNAL_TOOL,
    GET_UPCOMING_EVENTS_TOOL,
)

from app.tools.targeting_tools import (
    get_question_pool,
    get_member_context,
    get_member_edges,
    get_answered_questions,
    assign_question_to_member,
    get_all_members_for_targeting,
    GET_QUESTION_POOL_TOOL,
    GET_MEMBER_CONTEXT_TOOL,
    GET_MEMBER_EDGES_TOOL,
    GET_ANSWERED_QUESTIONS_TOOL,
    ASSIGN_QUESTION_TO_MEMBER_TOOL,
    GET_ALL_MEMBERS_FOR_TARGETING_TOOL,
)

from app.tools.group_tools import (
    get_present_member_profiles,
    get_group_edges,
    get_recent_group_questions,
    score_question_for_group,
    GET_PRESENT_MEMBER_PROFILES_TOOL,
    GET_GROUP_EDGES_TOOL,
    GET_RECENT_GROUP_QUESTIONS_TOOL,
    SCORE_QUESTION_FOR_GROUP_TOOL,
)

from app.tools.taste_tools import (
    get_conversation_history,
    get_question_responses,
    get_event_signals,
    get_current_taste_profile,
    update_taste_profile,
    GET_CONVERSATION_HISTORY_TOOL,
    GET_QUESTION_RESPONSES_TOOL,
    GET_EVENT_SIGNALS_TOOL as GET_TASTE_EVENT_SIGNALS_TOOL,
    GET_CURRENT_TASTE_PROFILE_TOOL,
    UPDATE_TASTE_PROFILE_TOOL,
)

__all__ = [
    # Graph tools
    "get_all_members_with_profiles",
    "get_existing_edges",
    "get_active_patterns",
    "save_edge",
    "GET_ALL_MEMBERS_TOOL",
    "GET_EXISTING_EDGES_TOOL",
    "GET_ACTIVE_PATTERNS_TOOL",
    "SAVE_EDGE_TOOL",
    # Question tools
    "get_community_profile_analysis",
    "get_member_gaps",
    "save_pattern",
    "GET_COMMUNITY_ANALYSIS_TOOL",
    "GET_MEMBER_GAPS_TOOL",
    "SAVE_QUESTION_DECK_TOOL",
    "GET_PATTERNS_TOOL",
    "SAVE_PATTERN_TOOL",
    # Event tools
    "get_member_event_signals",
    "record_event_signal",
    "get_upcoming_events",
    "compute_taste_affinity_scores",
    "GET_EVENT_SIGNALS_TOOL",
    "RECORD_EVENT_SIGNAL_TOOL",
    "GET_UPCOMING_EVENTS_TOOL",
    # Targeting tools
    "get_question_pool",
    "get_member_context",
    "get_member_edges",
    "get_answered_questions",
    "assign_question_to_member",
    "get_all_members_for_targeting",
    "GET_QUESTION_POOL_TOOL",
    "GET_MEMBER_CONTEXT_TOOL",
    "GET_MEMBER_EDGES_TOOL",
    "GET_ANSWERED_QUESTIONS_TOOL",
    "ASSIGN_QUESTION_TO_MEMBER_TOOL",
    "GET_ALL_MEMBERS_FOR_TARGETING_TOOL",
    # Group tools
    "get_present_member_profiles",
    "get_group_edges",
    "get_recent_group_questions",
    "score_question_for_group",
    "GET_PRESENT_MEMBER_PROFILES_TOOL",
    "GET_GROUP_EDGES_TOOL",
    "GET_RECENT_GROUP_QUESTIONS_TOOL",
    "SCORE_QUESTION_FOR_GROUP_TOOL",
    # Taste tools
    "get_conversation_history",
    "get_question_responses",
    "get_event_signals",
    "get_current_taste_profile",
    "update_taste_profile",
    "GET_CONVERSATION_HISTORY_TOOL",
    "GET_QUESTION_RESPONSES_TOOL",
    "GET_TASTE_EVENT_SIGNALS_TOOL",
    "GET_CURRENT_TASTE_PROFILE_TOOL",
    "UPDATE_TASTE_PROFILE_TOOL",
]
