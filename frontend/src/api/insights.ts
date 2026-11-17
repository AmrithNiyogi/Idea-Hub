import { apiFetch } from './client';
import type { InsightsDashboard } from '../types/phase456';

export const insightsApi = {
  dashboard: (days = 90) =>
    apiFetch<InsightsDashboard>(`/insights?days=${days}`),
};
