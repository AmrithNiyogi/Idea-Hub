/** Types for the AI Newsletter. */

export interface NewsCategory {
  slug: string;
  label: string;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  why_it_matters: string;
  source_name: string;
  url: string;
  published_at: string;
}

export interface NewsFeed {
  category: string;
  label: string;
  source: 'sample' | 'arxiv' | 'github';
  brief: string;
  items: NewsItem[];
  refreshed_at: string | null;
  stale: boolean;
  error: string | null;
}

export interface NewsRepo {
  name: string;
  url: string;
  description: string;
  stars: number;
  language: string;
}

export interface NewsPaperTopic {
  label: string;
  count: number;
  latest_title: string;
  latest_url: string;
}

export interface NewsTopic {
  topic: string;
  count: number;
}

export interface NewsInsights {
  trending_repos: NewsRepo[];
  paper_topics: NewsPaperTopic[];
  top_topics: NewsTopic[];
  generated_at: string;
  unavailable: string[];
}
