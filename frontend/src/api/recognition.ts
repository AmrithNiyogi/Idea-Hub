/** Recognition API — rules, leaderboard, awards, ledger. */

import { apiFetch } from './client';
import type {
  Award,
  LeaderboardRow,
  LedgerEntry,
  Level,
  RecognitionRules,
  ThanksItem,
} from '../types/recognition';

export const recognitionApi = {
  rules: () => apiFetch<RecognitionRules>('/recognition/rules'),

  leaderboard: (limit = 50, period: 'all' | 'quarter' | 'year' | 'week' = 'all') =>
    apiFetch<LeaderboardRow[]>(`/recognition/leaderboard?limit=${limit}&period=${period}`),

  awards: () => apiFetch<Award[]>('/recognition/awards'),

  sendThanks: (toUserId: string, note: string) =>
    apiFetch<ThanksItem>('/recognition/thanks', {
      method: 'POST',
      body: JSON.stringify({ to_user_id: toUserId, note }),
    }),

  recentThanks: (limit = 12) =>
    apiFetch<ThanksItem[]>(`/recognition/thanks?limit=${limit}`),

  confirmIoq: (period: string, ideaId: string, reason: string) =>
    apiFetch<Award>('/recognition/awards/ioq', {
      method: 'POST',
      body: JSON.stringify({ period, idea_id: ideaId, reason }),
    }),

  confirmAnnual: (year: string, userId: string, reason: string) =>
    apiFetch<Award>('/recognition/awards/annual', {
      method: 'POST',
      body: JSON.stringify({ year, user_id: userId, reason }),
    }),

  ledger: (userId: string) =>
    apiFetch<LedgerEntry[]>(`/recognition/users/${userId}/ledger`),

  level: (userId: string) =>
    apiFetch<Level>(`/recognition/users/${userId}/level`),
};
