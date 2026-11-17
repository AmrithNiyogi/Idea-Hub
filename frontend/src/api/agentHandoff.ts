/**
 * Agent handoff skill-pack downloads (Cursor / Claude Code).
 *
 * Auth: same cookie credentials as spine APIs.
 */

import { http, getApiErrorMessage } from './http';
import type { AgentSkillPack } from '../types/idea';

function wrap<T>(fn: () => Promise<T>): Promise<T> {
  return fn().catch((e) => {
    throw e instanceof Error ? e : new Error(getApiErrorMessage(e));
  });
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const agentHandoffApi = {
  skill(): Promise<AgentSkillPack> {
    return wrap(
      async () => (await http.get<AgentSkillPack>('/agent-handoff/skill')).data,
    );
  },

  /**
   * Download the installable zip (Cursor + Claude skill paths + README).
   */
  async downloadSkillZip(): Promise<void> {
    return wrap(async () => {
      const res = await http.get<Blob>('/agent-handoff/skill-pack.zip', {
        responseType: 'blob',
      });
      const disposition = res.headers['content-disposition'] as
        | string
        | undefined;
      const match = disposition?.match(/filename="?([^"]+)"?/i);
      const filename = match?.[1] ?? 'idea-hub-pull-idea-skill.zip';
      triggerBrowserDownload(res.data, filename);
    });
  },
};
