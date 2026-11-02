export type Difficulty = "Easy" | "Medium" | "Hard";
export type Status = "todo" | "attempted" | "solved";

export interface Question {
  id: number;
  slug: string;
  title: string;
  difficulty: Difficulty;
  url: string;
  platform: string;
  topics: string[];
  patterns: string[];
  companies: { name: string; frequency: number }[];
  sheets: string[];
  section: string | null;
  status: Status;
  confidence: number | null;
  attempts: number;
}

export interface SheetSummary {
  slug: string;
  name: string;
  description: string;
  kind: "curated" | "company" | "custom";
  total: number;
  solved: number;
}

export interface Badge { code: string; name: string; description: string; earned_at: string | null }
export interface Mastery { topic: string; solved: number; total: number; mastery: number }

export interface Dashboard {
  user: { name: string; xp: number; level: number; level_floor_xp: number; next_level_xp: number };
  solved: { total: number; Easy: number; Medium: number; Hard: number };
  total_questions: number;
  solved_today: number;
  streak: { current: number; longest: number };
  heatmap: { date: string; count: number }[];
  study_week: { date: string; minutes: number }[];
  study_hours_total: number;
  strong_topics: Mastery[];
  weak_topics: Mastery[];
  revision_due: number;
  career: Record<string, number>;
  badges: Badge[];
}

export interface Contest { platform: string; name: string; url: string; start: string; duration_min: number }

export interface Job {
  id: string;
  company: string;
  title: string;
  location: string;
  remote: boolean;
  india: boolean;
  url: string;
  source: string;
  posted_at: string | null;
  level: "intern" | "entry" | "mid" | "senior";
  tags: string[];
}

export interface JobsResponse { total: number; items: Job[]; companies: { name: string; count: number }[] }

export interface CompanyProfile {
  name: string;
  careers: string;
  linkedin: string;
  roles: string[];
  process: string[];
  focus: string[];
  open_roles: number;
  india_roles: number;
  recent: Job[];
  featured: boolean;
}

export interface Resource {
  id: number | null;
  title: string;
  author: string;
  kind: "book" | "notes" | "cheatsheet" | "practice" | "course" | "video";
  tags: string[];
  url: string;
  description: string;
  mine: boolean;
}

export interface RevisionItem {
  id: number;
  question: { id: number; title: string; difficulty: Difficulty; url: string };
  stage: number;
  interval_days: number;
  due_on: string;
  lapses: number;
  completed: boolean;
}

export interface Note {
  id: number;
  kind: "question" | "topic" | "ai" | "personal" | "interview";
  title: string;
  content: string;
  question_id: number | null;
  topic: string | null;
  updated_at: string | null;
}

export interface Application {
  id: number;
  company: string;
  role: string;
  status: "applied" | "oa" | "interview" | "offer" | "rejected";
  applied_on: string | null;
  next_step_on: string | null;
  link: string | null;
  notes: string;
}

export interface Readiness {
  company: string;
  readiness: number;
  coverage: number;
  solved: number;
  total: number;
  weak_topics: string[];
  next_questions: { id: number; title: string; difficulty: Difficulty; url: string; frequency: number }[];
}
