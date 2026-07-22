import type {
  Camera,
  PaginatedResponse,
  ProcessingJob,
  ProcessingJobStatus,
  ReviewStatus,
  Video,
  VideoStatus,
  ViolationEvent,
  ViolationType,
} from "@/types/api";

import {
  apiFetch,
  createApiUrl,
} from "./client";
import { createQueryPath } from "./query";

type VideoListParameters = {
  offset?: number;
  limit?: number;
  status?: VideoStatus;
  cameraId?: string;
};

type JobListParameters = {
  offset?: number;
  limit?: number;
  status?: ProcessingJobStatus;
  videoId?: string;
};

type ViolationListParameters = {
  offset?: number;
  limit?: number;
  violationType?: ViolationType;
  reviewStatus?: ReviewStatus;
  videoId?: string;
  processingJobId?: string;
  cameraId?: string;
};

type CameraListParameters = {
  offset?: number;
  limit?: number;
  status?: string;
};

export async function getVideos(
  parameters: VideoListParameters = {},
): Promise<PaginatedResponse<Video>> {
  return apiFetch(
    createQueryPath(
      "/videos",
      {
        offset: parameters.offset,
        limit: parameters.limit,
        status: parameters.status,
        camera_id: parameters.cameraId,
      },
    ),
  );
}


export async function deleteVideo(
  videoId: string,
): Promise<void> {
  return apiFetch<void>(
    `/videos/${encodeURIComponent(
      videoId,
    )}`,
    {
      method: "DELETE",
    },
  );
}

export async function getProcessingJobs(
  parameters: JobListParameters = {},
): Promise<
  PaginatedResponse<ProcessingJob>
> {
  return apiFetch(
    createQueryPath(
      "/jobs",
      {
        offset: parameters.offset,
        limit: parameters.limit,
        status: parameters.status,
        video_id: parameters.videoId,
      },
    ),
  );
}

export async function getViolations(
  parameters: ViolationListParameters = {},
): Promise<
  PaginatedResponse<ViolationEvent>
> {
  return apiFetch(
    createQueryPath(
      "/violations",
      {
        offset: parameters.offset,
        limit: parameters.limit,
        violation_type:
          parameters.violationType,
        review_status:
          parameters.reviewStatus,
        video_id: parameters.videoId,
        processing_job_id:
          parameters.processingJobId,
        camera_id: parameters.cameraId,
      },
    ),
  );
}

export async function getCameras(
  parameters: CameraListParameters = {},
): Promise<PaginatedResponse<Camera>> {
  return apiFetch(
    createQueryPath(
      "/cameras",
      {
        offset: parameters.offset,
        limit: parameters.limit,
        status: parameters.status,
      },
    ),
  );
}

export async function isBackendHealthy(): Promise<boolean> {
  try {
    const response = await fetch(
      createApiUrl("/health"),
      {
        cache: "no-store",
      },
    );

    return response.ok;
  } catch {
    return false;
  }
}

export type UploadVideoParameters = {
  file: File;
  cameraId?: string;
  priority?: number;
  onProgress?: (
    progressPercent: number,
  ) => void;
};

export function uploadVideo({
  file,
  cameraId,
  priority = 0,
  onProgress,
}: UploadVideoParameters): Promise<
  import("@/types/api").VideoUploadResponse
> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();

    request.withCredentials = true;

    request.open(
      "POST",
      createApiUrl("/videos/upload"),
    );

    request.setRequestHeader(
      "Accept",
      "application/json",
    );

    request.upload.addEventListener(
      "progress",
      (event) => {
        if (
          !event.lengthComputable ||
          !onProgress
        ) {
          return;
        }

        onProgress(
          Math.round(
            (event.loaded / event.total) * 100,
          ),
        );
      },
    );

    request.addEventListener(
      "load",
      () => {
        let body: unknown;

        try {
          body = JSON.parse(
            request.responseText,
          );
        } catch {
          body = null;
        }

        if (
          request.status >= 200 &&
          request.status < 300
        ) {
          resolve(
            body as import(
              "@/types/api"
            ).VideoUploadResponse,
          );

          return;
        }

        const detail =
          typeof body === "object" &&
          body !== null &&
          "detail" in body &&
          typeof body.detail === "string"
            ? body.detail
            : `Upload failed with status ${request.status}.`;

        reject(
          new Error(detail),
        );
      },
    );

    request.addEventListener(
      "error",
      () => {
        reject(
          new Error(
            "Unable to connect to the backend API.",
          ),
        );
      },
    );

    request.addEventListener(
      "abort",
      () => {
        reject(
          new Error("Upload was cancelled."),
        );
      },
    );

    const formData = new FormData();

    formData.append("file", file);

    if (cameraId) {
      formData.append(
        "camera_id",
        cameraId,
      );
    }

    formData.append(
      "priority",
      String(priority),
    );

    request.send(formData);
  });
}


export async function getProcessingJob(
  jobId: string,
): Promise<import("@/types/api").ProcessingJob> {
  return apiFetch<
    import("@/types/api").ProcessingJob
  >(
    `/jobs/${encodeURIComponent(jobId)}`,
  );
}


export function getProcessingJobPreviewUrl(
  jobId: string,
): string {
  const apiBaseUrl = (
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");

  return (
    `${apiBaseUrl}/jobs/` +
    `${encodeURIComponent(jobId)}/preview`
  );
}
