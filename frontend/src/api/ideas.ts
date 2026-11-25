import { http, getApiErrorMessage } from './http';
import type {
  AgentContext,
  Category,
  Comment,
  HomeAggregates,
  Idea,
  IdeaListResponse,
  IdeaWrite,
  ToggleResponse,
} from '../types/idea';

export interface IdeaListParams {
  q?: string;
  status?: string | string[];
  category_id?: string;
  tag?: string;
  author_id?: string;
  following?: boolean;
  include_drafts?: boolean;
  limit?: number;
  offset?: number;
}

function toParams(params: IdeaListParams): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (params.q) out.q = params.q;
  if (params.category_id) out.category_id = params.category_id;
  if (params.tag) out.tag = params.tag;
  if (params.author_id) out.author_id = params.author_id;
  if (params.following) out.following = true;
  if (params.include_drafts) out.include_drafts = true;
  if (params.limit != null) out.limit = params.limit;
  if (params.offset != null) out.offset = params.offset;
  if (params.status) out.status = params.status;
  return out;
}

async function wrap<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export const ideasApi = {
  list(params: IdeaListParams = {}): Promise<IdeaListResponse> {
    return wrap(async () => {
      const res = await http.get<IdeaListResponse>('/ideas', {
        params: toParams(params),
        paramsSerializer: {
          indexes: null,
        },
      });
      return res.data;
    });
  },

  home(): Promise<HomeAggregates> {
    return wrap(async () => (await http.get<HomeAggregates>('/ideas/home')).data);
  },

  get(id: string): Promise<Idea> {
    return wrap(async () => (await http.get<Idea>(`/ideas/${id}`)).data);
  },

  saveDraft(data: IdeaWrite, draftId?: string | null): Promise<Idea> {
    return wrap(async () => {
      const res = await http.post<Idea>('/ideas/drafts', {
        draft_id: draftId ?? null,
        data,
      });
      return res.data;
    });
  },

  submit(data: IdeaWrite, draftId?: string | null): Promise<Idea> {
    return wrap(async () => {
      const res = await http.post<Idea>('/ideas/submit', {
        draft_id: draftId ?? null,
        data,
      });
      return res.data;
    });
  },

  withdraw(id: string, reason = ''): Promise<Idea> {
    return wrap(
      async () =>
        (await http.post<Idea>(`/ideas/${id}/withdraw`, { reason })).data,
    );
  },

  restore(id: string): Promise<Idea> {
    return wrap(async () => (await http.post<Idea>(`/ideas/${id}/restore`)).data);
  },

  answerInfo(id: string, text: string): Promise<Idea> {
    return wrap(
      async () =>
        (await http.post<Idea>(`/ideas/${id}/answer-info`, { text })).data,
    );
  },

  vote(id: string): Promise<ToggleResponse> {
    return wrap(
      async () =>
        (await http.post<ToggleResponse>(`/ideas/${id}/vote`)).data,
    );
  },

  follow(id: string): Promise<ToggleResponse> {
    return wrap(
      async () =>
        (await http.post<ToggleResponse>(`/ideas/${id}/follow`)).data,
    );
  },

  listComments(id: string): Promise<Comment[]> {
    return wrap(
      async () =>
        (await http.get<Comment[]>(`/ideas/${id}/comments`)).data,
    );
  },

  addComment(id: string, body: string): Promise<Comment> {
    return wrap(
      async () =>
        (await http.post<Comment>(`/ideas/${id}/comments`, { body })).data,
    );
  },

  categories(): Promise<Category[]> {
    return wrap(
      async () => (await http.get<Category[]>('/categories')).data,
    );
  },

  agentContext(id: string): Promise<AgentContext> {
    return wrap(
      async () =>
        (await http.get<AgentContext>(`/ideas/${id}/agent-context`)).data,
    );
  },
};
