import {
  apiFetch,
} from "@/lib/api/client";
import type {
  ViolationEvent,
  ViolationListResponse,
  ViolationQuery,
} from "@/types/violations";


const apiBaseUrl = (
  process.env
    .NEXT_PUBLIC_API_BASE_URL
  ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");


export async function getViolations(
  query: ViolationQuery = {},
): Promise<ViolationListResponse> {
  const parameters =
    new URLSearchParams();

  parameters.set(
    "offset",
    String(
      query.offset ?? 0,
    ),
  );

  parameters.set(
    "limit",
    String(
      query.limit ?? 100,
    ),
  );

  if (query.violationType) {
    parameters.set(
      "violation_type",
      query.violationType,
    );
  }

  if (query.reviewStatus) {
    parameters.set(
      "review_status",
      query.reviewStatus,
    );
  }

  if (query.videoId) {
    parameters.set(
      "video_id",
      query.videoId,
    );
  }

  if (
    query.processingJobId
  ) {
    parameters.set(
      "processing_job_id",
      query.processingJobId,
    );
  }

  if (query.cameraId) {
    parameters.set(
      "camera_id",
      query.cameraId,
    );
  }

  return apiFetch<
    ViolationListResponse
  >(
    `/violations?${parameters.toString()}`,
  );
}


export async function getViolation(
  violationId: string,
): Promise<ViolationEvent> {
  return apiFetch<
    ViolationEvent
  >(
    `/violations/${encodeURIComponent(
      violationId,
    )}`,
  );
}


export function getViolationImageUrl(
  violationId: string,
): string {
  return (
    `${apiBaseUrl}/violations/`
    + `${encodeURIComponent(
      violationId,
    )}/evidence/image`
  );
}


export function getViolationClipUrl(
  violationId: string,
): string {
  return (
    `${apiBaseUrl}/violations/`
    + `${encodeURIComponent(
      violationId,
    )}/evidence/clip`
  );
}


export async function reviewViolation(
  violationId: string,
  payload: import(
    "@/types/violations"
  ).ViolationReviewPayload,
): Promise<ViolationEvent> {
  return apiFetch<
    ViolationEvent
  >(
    `/violations/${encodeURIComponent(
      violationId,
    )}/review`,
    {
      method: "PATCH",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify(
        payload,
      ),
    },
  );
}
