import { apiFetch } from './client';
import type { NewsCategory, NewsFeed, NewsInsights } from '../types/news';

export const newsApi = {
  categories: () => apiFetch<NewsCategory[]>('/news/categories'),

  insights: () => apiFetch<NewsInsights>('/news/insights'),

  feed: (category: string) =>
    apiFetch<NewsFeed>(`/news?category=${encodeURIComponent(category)}`),

  refresh: (category: string, force = false) =>
    apiFetch<NewsFeed>(
      `/news/${encodeURIComponent(category)}/refresh${force ? '?force=true' : ''}`,
      { method: 'POST' },
    ),
};
