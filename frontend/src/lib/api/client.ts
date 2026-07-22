const fallbackBrowserApiBaseUrl =
  "/api/v1";

const fallbackServerApiBaseUrl =
  "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getApiBaseUrl(): string {
  const baseUrl =
    typeof window === "undefined"
      ? (
          process.env
            .BACKEND_API_BASE_URL ??
          fallbackServerApiBaseUrl
        )
      : (
          process.env
            .NEXT_PUBLIC_API_BASE_URL ??
          fallbackBrowserApiBaseUrl
        );

  return baseUrl.replace(/\/$/, "");
}

export function createApiUrl(
  path: string,
): string {
  const normalizedPath =
    path.startsWith("/")
      ? path
      : `/${path}`;

  return (
    `${getApiBaseUrl()}` +
    `${normalizedPath}`
  );
}

export function createApiHeaders(
  initialHeaders?: HeadersInit,
): Headers {
  const headers = new Headers(
    initialHeaders,
  );

  if (!headers.has("Accept")) {
    headers.set(
      "Accept",
      "application/json",
    );
  }

  if (
    typeof window === "undefined"
  ) {
    const internalApiKey =
      process.env
        .BACKEND_INTERNAL_API_KEY;

    if (internalApiKey) {
      headers.set(
        "X-Internal-API-Key",
        internalApiKey,
      );
    }
  }

  return headers;
}

async function readErrorMessage(
  response: Response,
): Promise<string> {
  const fallback =
    `API request failed with status ${response.status}.`;

  try {
    const body =
      (await response.json()) as {
        detail?: unknown;
      };

    if (
      typeof body.detail ===
        "string" &&
      body.detail.trim()
    ) {
      return body.detail;
    }

    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => {
          if (
            typeof item ===
              "object" &&
            item !== null &&
            "msg" in item &&
            typeof item.msg ===
              "string"
          ) {
            return item.msg;
          }

          return (
            "The request contains " +
            "invalid information."
          );
        })
        .join(" ");
    }
  } catch {
    // Preserve the fallback.
  }

  return fallback;
}

async function clearExpiredSession() {
  if (
    typeof window === "undefined"
  ) {
    return;
  }

  try {
    await fetch(
      "/api/auth/logout",
      {
        method: "POST",
      },
    );
  } finally {
    window.location.assign(
      "/login",
    );
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers =
    createApiHeaders(
      options.headers,
    );

  let response: Response;

  try {
    response = await fetch(
      createApiUrl(path),
      {
        ...options,
        headers,
        cache:
          options.cache ??
          "no-store",
        credentials:
          options.credentials ??
          "include",
      },
    );
  } catch {
    throw new ApiError(
      "Unable to connect to the backend API.",
      0,
    );
  }

  if (!response.ok) {
    const message =
      await readErrorMessage(
        response,
      );

    if (response.status === 401) {
      await clearExpiredSession();
    }

    throw new ApiError(
      message,
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (
    await response.json()
  ) as T;
}
