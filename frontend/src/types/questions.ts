// Types for mobile question flow

export interface MemberContext {
  id: number;
  first_name: string | null;
  last_name: string | null;
}

export interface PatternContext {
  id: number;
  name: string;
  category: string;
}

export interface MobileQuestionData {
  id: number;
  delivery_id: number;
  question_text: string;
  question_type: 'free_form' | 'multiple_choice' | 'yes_no' | 'fill_in_blank';
  category: string;
  vibe: 'warm' | 'playful' | 'deep' | 'edgy' | 'connector' | null;
  difficulty_level: number;
  options: string[];
  blank_prompt: string | null;
  purpose: string;
  notes: string | null;
  related_members: MemberContext[];
  related_pattern: PatternContext | null;
  questions_answered_today: number;
  questions_remaining: number;
}
