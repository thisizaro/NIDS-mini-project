export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeout || 60000);

  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail;
      try {
        const body = await response.json();
        detail = body.detail || response.statusText;
      } catch {
        detail = response.statusText;
      }
      throw new ApiError(response.status, detail);
    }

    return response;
  } finally {
    clearTimeout(timeout);
  }
}
