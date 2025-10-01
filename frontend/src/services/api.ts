// Basit API istemcisi: Backend URL'ini merkezi yönetin

export const API_BASE_URL: string =
  (import.meta as any)?.env?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

export type AskRequest = {
  question: string;
  model?: string;
  session_id?: string;
};

export type SourceLink = { title?: string; url?: string };

export type AskResponse = {
  answer: string;
  sources: any[];
  source_links: SourceLink[];
  response_time: string;
  chunks_used: number;
  model: string;
  timestamp: string;
  action_buttons?: any[];
  special_response?: boolean;
  special_type?: string | null;
};

export async function askApi(payload: AskRequest, signal?: AbortSignal): Promise<AskResponse> {
  const res = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`ASK_FAILED ${res.status}: ${text}`);
  }
  return (await res.json()) as AskResponse;
}

export async function ingestTranscriptApi(
  params: { text: string; title?: string; url?: string; author?: string; clean?: boolean },
  signal?: AbortSignal,
): Promise<any> {
  const form = new FormData();
  form.set('text', params.text);
  form.set('title', params.title ?? 'Video Transcript');
  form.set('url', params.url ?? '');
  form.set('author', params.author ?? 'Video');
  form.set('clean', String(params.clean ?? true));

  const res = await fetch(`${API_BASE_URL}/ingest/transcript`, {
    method: 'POST',
    body: form,
    signal,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`INGEST_TRANSCRIPT_FAILED ${res.status}: ${text}`);
  }
  return await res.json();
}

export async function ingestVideoApi(
  params: { file: File; language?: string; title?: string; url?: string; author?: string; clean?: boolean; dry_run?: boolean },
  signal?: AbortSignal,
): Promise<any> {
  const form = new FormData();
  form.set('file', params.file);
  form.set('language', params.language ?? 'tr');
  form.set('title', params.title ?? params.file.name);
  form.set('url', params.url ?? '');
  form.set('author', params.author ?? 'Video');
  form.set('clean', String(params.clean ?? true));
  form.set('dry_run', String(params.dry_run ?? false));

  const res = await fetch(`${API_BASE_URL}/ingest/video`, {
    method: 'POST',
    body: form,
    signal,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`INGEST_VIDEO_FAILED ${res.status}: ${text}`);
  }
  return await res.json();
}


