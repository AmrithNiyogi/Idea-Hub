import { http, getApiErrorMessage } from './http';
import type { Idea } from '../types/idea';
import type {
  DecideRequest,
  Decision,
  ReviewQueueItem,
  ReviewScores,
} from '../types/review';

async function wrap<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export const reviewApi = {
  queue(): Promise<ReviewQueueItem[]> {
    return wrap(
      async () => (await http.get<ReviewQueueItem[]>('/review/queue')).data,
    );
  },

  pickup(ideaId: string): Promise<Idea> {
    return wrap(
      async () =>
        (await http.post<Idea>(`/review/${ideaId}/pickup`)).data,
    );
  },

  saveScores(ideaId: string, scores: ReviewScores): Promise<ReviewScores & { id?: string }> {
    return wrap(
      async () =>
        (await http.post(`/review/${ideaId}/scores`, scores)).data,
    );
  },

  decide(ideaId: string, body: DecideRequest): Promise<Decision> {
    return wrap(
      async () =>
        (await http.post<Decision>(`/review/${ideaId}/decide`, body)).data,
    );
  },
};
