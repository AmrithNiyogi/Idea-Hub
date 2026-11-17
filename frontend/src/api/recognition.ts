/** Recognition API — rules, leaderboard, awards, ledger. */

import { apiFetch } from './client';
import type {
  Award,
  LeaderboardRow,
  LedgerEntry,
  Level,
  RecognitionRules,
} from '../types/recognition';

export const recognitionApi = {
  rules: () => apiFetch<RecognitionRules>('/recognition/rules'),

  leaderboard: (limit = 50) =>
    apiFetch<LeaderboardRow[]>(`/recognition/leaderboard?limit=${limit}`),

  awards: () => apiFetch<Award[]>('/recognition/awards'),

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
