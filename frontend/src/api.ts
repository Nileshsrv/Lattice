export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request(method: string, url: string, body?: unknown): Promise<any> {
  const init: RequestInit = { method, credentials: "same-origin" };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const resp = await fetch(url, init);
  if (!resp.ok) {
    let detail: unknown;
    try {
      detail = (await resp.json()).detail;
    } catch {
      detail = resp.statusText;
    }
    throw new ApiError(resp.status, detail);
  }
  const type = resp.headers.get("content-type") ?? "";
  return type.includes("application/json") ? resp.json() : resp.text();
}

export const api = {
  get: (url: string) => request("GET", url),
  post: (url: string, body?: unknown) => request("POST", url, body),
  patch: (url: string, body?: unknown) => request("PATCH", url, body),
};
