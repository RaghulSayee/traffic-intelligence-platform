import type {
  Camera,
  PaginatedResponse,
  ProcessingJob,
  Video,
  ViolationEvent,
} from "@/types/api";

import {
  getCameras,
  getProcessingJobs,
  getVideos,
  getViolations,
  isBackendHealthy,
} from "./resources";

type AttemptResult<T> = {
  data: T;
  succeeded: boolean;
};

async function attempt<T>(
  promise: Promise<T>,
  fallback: T,
): Promise<AttemptResult<T>> {
  try {
    return {
      data: await promise,
      succeeded: true,
    };
  } catch {
    return {
      data: fallback,
      succeeded: false,
    };
  }
}

function emptyPage<T>(
  limit: number,
): PaginatedResponse<T> {
  return {
    items: [],
    total: 0,
    offset: 0,
    limit,
  };
}

export async function getDashboardData() {
  const [
    backendOnline,
    videosResult,
    recentJobsResult,
    runningJobsResult,
    queuedJobsResult,
    completedJobsResult,
    violationsResult,
    pendingViolationsResult,
    camerasResult,
  ] = await Promise.all([
    isBackendHealthy(),

    attempt(
      getVideos({
        limit: 100,
      }),
      emptyPage<Video>(100),
    ),

    attempt(
      getProcessingJobs({
        limit: 5,
      }),
      emptyPage<ProcessingJob>(5),
    ),

    attempt(
      getProcessingJobs({
        limit: 1,
        status: "running",
      }),
      emptyPage<ProcessingJob>(1),
    ),

    attempt(
      getProcessingJobs({
        limit: 1,
        status: "queued",
      }),
      emptyPage<ProcessingJob>(1),
    ),

    attempt(
      getProcessingJobs({
        limit: 1,
        status: "succeeded",
      }),
      emptyPage<ProcessingJob>(1),
    ),

    attempt(
      getViolations({
        limit: 5,
      }),
      emptyPage<ViolationEvent>(5),
    ),

    attempt(
      getViolations({
        limit: 1,
        reviewStatus: "pending",
      }),
      emptyPage<ViolationEvent>(1),
    ),

    attempt(
      getCameras({
        limit: 100,
      }),
      emptyPage<Camera>(100),
    ),
  ]);

  const dataAvailable = [
    videosResult,
    recentJobsResult,
    runningJobsResult,
    queuedJobsResult,
    completedJobsResult,
    violationsResult,
    pendingViolationsResult,
    camerasResult,
  ].every((result) => result.succeeded);

  return {
    backendOnline,
    dataAvailable,
    videos: videosResult.data,
    recentJobs: recentJobsResult.data,
    activeJobCount:
      runningJobsResult.data.total +
      queuedJobsResult.data.total,
    completedJobCount:
      completedJobsResult.data.total,
    violations: violationsResult.data,
    pendingViolationCount:
      pendingViolationsResult.data.total,
    cameras: camerasResult.data,
  };
}
