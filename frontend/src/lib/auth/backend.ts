import "server-only";

const fallbackBackendUrl =
  "http://127.0.0.1:8000/api/v1";

export function getBackendApiBaseUrl(): string {
  return (
    process.env.BACKEND_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    fallbackBackendUrl
  ).replace(/\/$/, "");
}
