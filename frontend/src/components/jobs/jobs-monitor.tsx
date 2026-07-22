"use client";

import {
  AlertCircle,
  CheckCircle2,
  CircleOff,
  Clock3,
  Eye,
  FileVideo,
  ListChecks,
  LoaderCircle,
  MapPin,
  RefreshCw,
  Search,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import {
  useRouter,
} from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useTransition,
} from "react";

import {
  PaginationControls,
} from "@/components/ui/pagination-controls";

import {
  MobileTableNotice,
} from "@/components/ui/mobile-table-notice";

import type {
  Camera,
  ProcessingJob,
  ProcessingJobStatus,
  Video,
} from "@/types/api";

type JobsMonitorProps = {
  jobs: ProcessingJob[];
  videos: Video[];
  cameras: Camera[];
};

type StatusFilter =
  | ""
  | ProcessingJobStatus;

const statusLabels: Record<
  ProcessingJobStatus,
  string
> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  cancelled: "Cancelled",
};

const statusStyles: Record<
  ProcessingJobStatus,
  string
> = {
  queued:
    "border-slate-200 bg-slate-100 text-slate-700",
  running:
    "border-amber-200 bg-amber-50 text-amber-700",
  succeeded:
    "border-emerald-200 bg-emerald-50 text-emerald-700",
  failed:
    "border-rose-200 bg-rose-50 text-rose-700",
  cancelled:
    "border-slate-200 bg-slate-100 text-slate-500",
};

const statusIcons = {
  queued: Clock3,
  running: LoaderCircle,
  succeeded: CheckCircle2,
  failed: XCircle,
  cancelled: CircleOff,
};

function formatDate(
  value: string | null,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function formatDuration(
  job: ProcessingJob,
): string {
  if (
    !job.started_at ||
    !job.completed_at
  ) {
    return job.status === "running"
      ? "In progress"
      : "—";
  }

  const started =
    new Date(job.started_at).getTime();

  const completed =
    new Date(job.completed_at).getTime();

  if (
    Number.isNaN(started) ||
    Number.isNaN(completed) ||
    completed < started
  ) {
    return "—";
  }

  const seconds =
    (completed - started) / 1000;

  if (seconds < 60) {
    return `${seconds.toFixed(1)} sec`;
  }

  const minutes =
    Math.floor(seconds / 60);

  const remainingSeconds =
    Math.round(seconds % 60);

  return `${minutes}m ${remainingSeconds}s`;
}

function createUpdatedTimeLabel(): string {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    },
  ).format(new Date());
}

function clampProgress(
  value: number,
): number {
  if (!Number.isFinite(value)) {
    return 0;
  }

  return Math.min(
    100,
    Math.max(0, value),
  );
}

export function JobsMonitor({
  jobs,
  videos,
  cameras,
}: JobsMonitorProps) {
  const router = useRouter();

  const [
    isRefreshing,
    startRefresh,
  ] = useTransition();

  const [
    searchTerm,
    setSearchTerm,
  ] = useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState<StatusFilter>("");

  const [
    lastUpdatedLabel,
    setLastUpdatedLabel,
  ] = useState<string | null>(
    null,
  );

  const [
    currentPage,
    setCurrentPage,
  ] = useState(1);

  const [
    pageSize,
    setPageSize,
  ] = useState(10);

  const videosById =
    useMemo(
      () =>
        new Map(
          videos.map(
            (video) => [
              video.id,
              video,
            ],
          ),
        ),
      [videos],
    );

  const camerasById =
    useMemo(
      () =>
        new Map(
          cameras.map(
            (camera) => [
              camera.id,
              camera,
            ],
          ),
        ),
      [cameras],
    );

  const activeJobCount =
    jobs.filter(
      (job) =>
        job.status === "queued" ||
        job.status === "running",
    ).length;

  const succeededCount =
    jobs.filter(
      (job) =>
        job.status === "succeeded",
    ).length;

  const failedCount =
    jobs.filter(
      (job) =>
        job.status === "failed",
    ).length;

  const filteredJobs =
    useMemo(() => {
      const normalizedSearch =
        searchTerm
          .trim()
          .toLowerCase();

      return jobs.filter(
        (job) => {
          if (
            statusFilter &&
            job.status !== statusFilter
          ) {
            return false;
          }

          if (!normalizedSearch) {
            return true;
          }

          const video =
            videosById.get(
              job.video_id,
            );

          const camera =
            video?.camera_id
              ? camerasById.get(
                  video.camera_id,
                )
              : undefined;

          const searchableText = [
            job.id,
            job.pipeline_name,
            job.pipeline_version,
            job.worker_id,
            video?.original_filename,
            camera?.name,
            camera?.location,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          return searchableText.includes(
            normalizedSearch,
          );
        },
      );
    }, [
      camerasById,
      jobs,
      searchTerm,
      statusFilter,
      videosById,
    ]);

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        filteredJobs.length /
          pageSize,
      ),
    );

  const safeCurrentPage =
    Math.min(
      currentPage,
      totalPages,
    );

  const pageStartIndex =
    (
      safeCurrentPage - 1
    ) * pageSize;

  const pageEndIndex =
    Math.min(
      pageStartIndex +
        pageSize,
      filteredJobs.length,
    );

  const paginatedJobs =
    filteredJobs.slice(
      pageStartIndex,
      pageEndIndex,
    );

  const firstVisibleItem =
    filteredJobs.length
      ? pageStartIndex + 1
      : 0;

  const lastVisibleItem =
    filteredJobs.length
      ? pageEndIndex
      : 0;

  const refreshJobs =
    useCallback(() => {
      startRefresh(() => {
        router.refresh();

        setLastUpdatedLabel(
          createUpdatedTimeLabel(),
        );
      });
    }, [
      router,
      startRefresh,
    ]);

  useEffect(() => {
    if (activeJobCount === 0) {
      return;
    }

    const intervalId =
      window.setInterval(
        refreshJobs,
        5000,
      );

    return () => {
      window.clearInterval(
        intervalId,
      );
    };
  }, [
    activeJobCount,
    refreshJobs,
  ]);

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ListChecks
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Total jobs
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {jobs.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <LoaderCircle
            size={21}
            className={
              activeJobCount
                ? "animate-spin text-amber-600"
                : "text-amber-600"
            }
          />

          <p className="mt-4 text-sm text-slate-500">
            Active jobs
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {activeJobCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <CheckCircle2
            size={21}
            className="text-emerald-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Succeeded
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {succeededCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <XCircle
            size={21}
            className="text-rose-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Failed
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {failedCount}
          </p>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <h2 className="font-semibold text-slate-950">
              Job monitoring
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Search and monitor video-analysis jobs from the FastAPI backend.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <p className="text-xs text-slate-400">
              {lastUpdatedLabel
                ? `Last updated ${lastUpdatedLabel}`
                : "Waiting for refresh"}
            </p>

            <button
              type="button"
              onClick={refreshJobs}
              disabled={isRefreshing}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-wait disabled:text-slate-400"
            >
              <RefreshCw
                size={16}
                className={
                  isRefreshing
                    ? "animate-spin"
                    : ""
                }
              />

              Refresh
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-[1fr_240px_auto]">
          <label className="flex h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3">
            <Search
              size={17}
              className="text-slate-400"
            />

            <input
              type="search"
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(
                  event.target.value,
                );

                setCurrentPage(1);
              }}
              placeholder="Search job, video, camera or pipeline"
              className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
            />
          </label>

          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(
                event.target
                  .value as StatusFilter,
              );

              setCurrentPage(1);
            }}
            className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-cyan-400"
          >
            <option value="">
              All statuses
            </option>

            <option value="queued">
              Queued
            </option>

            <option value="running">
              Running
            </option>

            <option value="succeeded">
              Succeeded
            </option>

            <option value="failed">
              Failed
            </option>

            <option value="cancelled">
              Cancelled
            </option>
          </select>

          <button
            type="button"
            onClick={() => {
              setSearchTerm("");
              setStatusFilter("");
              setCurrentPage(1);
            }}
            className="h-11 w-full rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-600 lg:w-auto hover:bg-slate-50"
          >
            Clear
          </button>
        </div>

        {activeJobCount > 0 ? (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <LoaderCircle
              size={17}
              className="animate-spin"
            />

            Active jobs are refreshed automatically every five seconds.
          </div>
        ) : null}
      </section>

      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {filteredJobs.length ? (
          <>
          <MobileTableNotice />

          <div className="overflow-x-auto overscroll-x-contain touch-pan-x [scrollbar-width:thin]">
            <table className="w-full min-w-[1150px] text-left">
              <thead className="bg-slate-50">
                <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4">
                    Video
                  </th>

                  <th className="px-5 py-4">
                    Camera
                  </th>

                  <th className="px-5 py-4">
                    Status
                  </th>

                  <th className="px-5 py-4">
                    Progress
                  </th>

                  <th className="px-5 py-4">
                    Pipeline
                  </th>

                  <th className="px-5 py-4">
                    Duration
                  </th>

                  <th className="px-5 py-4">
                    Created
                  </th>

                  <th className="px-5 py-4 text-right">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {paginatedJobs.map(
                  (job) => {
                    const video =
                      videosById.get(
                        job.video_id,
                      );

                    const camera =
                      video?.camera_id
                        ? camerasById.get(
                            video.camera_id,
                          )
                        : undefined;

                    const StatusIcon =
                      statusIcons[
                        job.status
                      ];

                    const progress =
                      clampProgress(
                        job.progress_percent,
                      );

                    return (
                      <tr
                        key={job.id}
                        className="align-top hover:bg-slate-50/70"
                      >
                        <td className="px-5 py-4">
                          <div className="flex min-w-[260px] items-start gap-3">
                            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
                              <FileVideo
                                size={19}
                              />
                            </span>

                            <div className="min-w-0">
                              <p
                                title={
                                  video?.original_filename
                                }
                                className="max-w-[280px] truncate text-sm font-semibold text-slate-950"
                              >
                                {video?.original_filename ??
                                  "Unknown video"}
                              </p>

                              <p className="mt-1 font-mono text-xs text-slate-400">
                                {job.id.slice(
                                  0,
                                  12,
                                )}
                              </p>
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          {camera ? (
                            <>
                              <p className="text-sm font-semibold text-slate-800">
                                {camera.name}
                              </p>

                              <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                                <MapPin
                                  size={12}
                                />

                                {camera.location ??
                                  "No location"}
                              </p>
                            </>
                          ) : (
                            <p className="text-sm text-slate-400">
                              Unassigned
                            </p>
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={[
                              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold",
                              statusStyles[
                                job.status
                              ],
                            ].join(" ")}
                          >
                            <StatusIcon
                              size={14}
                              className={
                                job.status ===
                                "running"
                                  ? "animate-spin"
                                  : ""
                              }
                            />

                            {
                              statusLabels[
                                job.status
                              ]
                            }
                          </span>

                          {job.error_message ? (
                            <p
                              title={
                                job.error_message
                              }
                              className="mt-2 max-w-[180px] truncate text-xs text-rose-600"
                            >
                              {job.error_message}
                            </p>
                          ) : null}
                        </td>

                        <td className="px-5 py-4">
                          <div className="min-w-[150px]">
                            <div className="flex items-center justify-between gap-3 text-xs">
                              <span className="text-slate-500">
                                Frame{" "}
                                {
                                  job.last_processed_frame
                                }
                              </span>

                              <span className="font-semibold text-slate-800">
                                {Math.round(
                                  progress,
                                )}
                                %
                              </span>
                            </div>

                            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                              <div
                                className={[
                                  "h-full rounded-full transition-all",
                                  job.status ===
                                  "failed"
                                    ? "bg-rose-500"
                                    : job.status ===
                                        "succeeded"
                                      ? "bg-emerald-500"
                                      : "bg-cyan-500",
                                ].join(" ")}
                                style={{
                                  width: `${progress}%`,
                                }}
                              />
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <p className="text-sm font-semibold text-slate-800">
                            {job.pipeline_name}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            Version{" "}
                            {job.pipeline_version ??
                              "—"}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            Attempt{" "}
                            {job.attempt_count}
                          </p>
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-500">
                          {formatDuration(
                            job,
                          )}
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-500">
                          {formatDate(
                            job.created_at,
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <div className="flex flex-wrap justify-end gap-2">
                            {video ? (
                              <Link
                                href={`/videos/${video.id}`}
                                className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 px-3 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                              >
                                Video
                              </Link>
                            ) : null}

                            <Link
                              href={`/jobs/${job.id}`}
                              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-cyan-500 px-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
                            >
                              <Eye size={16} />
                              Details
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>
          </>
        ) : (
          <div className="px-6 py-16 text-center">
            {jobs.length ? (
              <Search
                size={36}
                className="mx-auto text-slate-300"
              />
            ) : (
              <ListChecks
                size={36}
                className="mx-auto text-slate-300"
              />
            )}

            <h3 className="mt-4 font-semibold text-slate-950">
              {jobs.length
                ? "No matching jobs"
                : "No processing jobs yet"}
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              {jobs.length
                ? "Change or clear the search filters."
                : "Upload a traffic video to create the first analysis job."}
            </p>

            {!jobs.length ? (
              <Link
                href="/videos/upload"
                className="mt-5 inline-flex h-10 items-center justify-center rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
              >
                Upload video
              </Link>
            ) : null}
          </div>
        )}

        {filteredJobs.length ? (
          <PaginationControls
            currentPage={
              safeCurrentPage
            }
            totalPages={
              totalPages
            }
            pageSize={
              pageSize
            }
            totalItems={
              filteredJobs.length
            }
            startItem={
              firstVisibleItem
            }
            endItem={
              lastVisibleItem
            }
            disabled={
              isRefreshing
            }
            onPageChange={
              setCurrentPage
            }
            onPageSizeChange={(
              nextPageSize,
            ) => {
              setPageSize(
                nextPageSize,
              );

              setCurrentPage(1);
            }}
          />
        ) : null}
      </section>

      {failedCount > 0 ? (
        <section className="mt-6 flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-5">
          <AlertCircle
            size={20}
            className="mt-0.5 shrink-0 text-rose-600"
          />

          <div>
            <h3 className="font-semibold text-rose-800">
              Failed jobs require attention
            </h3>

            <p className="mt-1 text-sm text-rose-700">
              Open the failed job details to inspect its error message and processing metrics.
            </p>
          </div>
        </section>
      ) : null}
    </>
  );
}
