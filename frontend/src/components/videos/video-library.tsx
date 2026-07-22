"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Eye,
  FileVideo,
  Filter,
  LoaderCircle,
  RefreshCw,
  Search,
  Upload,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import {
  useMemo,
  useState,
} from "react";

import {
  DeleteVideoButton,
} from "@/components/videos/delete-video-button";

import {
  PaginationControls,
} from "@/components/ui/pagination-controls";

import {
  MobileTableNotice,
} from "@/components/ui/mobile-table-notice";

import type {
  ProcessingJob,
  Video,
} from "@/types/api";

type CameraRecord = {
  id: string;
  name: string;
  location: string | null;
};

type VideoLibraryProps = {
  videos: Video[];
  jobs: ProcessingJob[];
  cameras: CameraRecord[];
};

type DerivedJobStatus =
  | "not_processed"
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

const statusStyles: Record<
  DerivedJobStatus,
  string
> = {
  not_processed:
    "bg-slate-100 text-slate-600",
  queued:
    "bg-slate-100 text-slate-700",
  running:
    "bg-amber-50 text-amber-700",
  succeeded:
    "bg-emerald-50 text-emerald-700",
  failed:
    "bg-rose-50 text-rose-700",
  cancelled:
    "bg-slate-100 text-slate-500",
};

const statusIcons = {
  not_processed: Clock3,
  queued: Clock3,
  running: LoaderCircle,
  succeeded: CheckCircle2,
  failed: XCircle,
  cancelled: XCircle,
};

function formatLabel(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}

function formatDate(
  value: string | null,
): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "Not available";
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function formatFileSize(
  value: number | null,
): string {
  if (
    value === null ||
    !Number.isFinite(value) ||
    value < 0
  ) {
    return "—";
  }

  const units = [
    "B",
    "KB",
    "MB",
    "GB",
  ];

  let size = value;
  let unitIndex = 0;

  while (
    size >= 1024 &&
    unitIndex < units.length - 1
  ) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(
    unitIndex === 0 ? 0 : 1,
  )} ${units[unitIndex]}`;
}

function formatDuration(
  value: number | null,
): string {
  if (
    value === null ||
    !Number.isFinite(value) ||
    value < 0
  ) {
    return "—";
  }

  const roundedSeconds =
    Math.round(value);

  const minutes =
    Math.floor(
      roundedSeconds / 60,
    );

  const seconds =
    roundedSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${seconds}s`;
}

function asRecord(
  value: unknown,
): Record<string, unknown> {
  if (
    typeof value === "object" &&
    value !== null
  ) {
    return value as Record<
      string,
      unknown
    >;
  }

  return {};
}

function getStringField(
  value: unknown,
  keys: string[],
): string | null {
  const record =
    asRecord(value);

  for (const key of keys) {
    const field =
      record[key];

    if (
      typeof field === "string" &&
      field.trim()
    ) {
      return field;
    }
  }

  return null;
}

function getNumberField(
  value: unknown,
  keys: string[],
): number | null {
  const record =
    asRecord(value);

  for (const key of keys) {
    const field =
      record[key];

    if (
      typeof field === "number" &&
      Number.isFinite(field)
    ) {
      return field;
    }
  }

  return null;
}

function getLatestJob(
  videoId: string,
  jobs: ProcessingJob[],
): ProcessingJob | undefined {
  return jobs
    .filter(
      (job) =>
        job.video_id === videoId,
    )
    .sort((first, second) => {
      return (
        new Date(
          second.created_at,
        ).getTime() -
        new Date(
          first.created_at,
        ).getTime()
      );
    })[0];
}

export function VideoLibrary({
  videos,
  jobs,
  cameras,
}: VideoLibraryProps) {
  const [
    searchValue,
    setSearchValue,
  ] = useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState<
    DerivedJobStatus | ""
  >("");

  const [
    currentPage,
    setCurrentPage,
  ] = useState(1);

  const [
    pageSize,
    setPageSize,
  ] = useState(10);

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

  const latestJobsByVideoId =
    useMemo(() => {
      const lookup =
        new Map<
          string,
          ProcessingJob
        >();

      for (const video of videos) {
        const latestJob =
          getLatestJob(
            video.id,
            jobs,
          );

        if (latestJob) {
          lookup.set(
            video.id,
            latestJob,
          );
        }
      }

      return lookup;
    }, [
      videos,
      jobs,
    ]);

  const processedVideos =
    useMemo(() => {
      return videos.map(
        (video) => {
          const metadata =
            asRecord(video);

          const latestJob =
            latestJobsByVideoId.get(
              video.id,
            );

          const jobStatus =
            (
              latestJob?.status ??
              "not_processed"
            ) as DerivedJobStatus;

          const cameraId =
            getStringField(
              metadata,
              [
                "camera_id",
                "cameraId",
              ],
            );

          const camera =
            cameraId
              ? camerasById.get(
                  cameraId,
                )
              : undefined;

          return {
            video,
            metadata,
            latestJob,
            jobStatus,
            camera,
            cameraId,
            fileSize:
              getNumberField(
                metadata,
                [
                  "file_size_bytes",
                  "size_bytes",
                  "file_size",
                ],
              ),
            duration:
              getNumberField(
                metadata,
                [
                  "duration_seconds",
                  "duration",
                ],
              ),
            createdAt:
              getStringField(
                metadata,
                [
                  "created_at",
                  "uploaded_at",
                ],
              ),
          };
        },
      );
    }, [
      videos,
      latestJobsByVideoId,
      camerasById,
    ]);

  const filteredVideos =
    useMemo(() => {
      const normalizedSearch =
        searchValue
          .trim()
          .toLowerCase();

      return processedVideos.filter(
        (item) => {
          if (
            statusFilter &&
            item.jobStatus !==
              statusFilter
          ) {
            return false;
          }

          if (!normalizedSearch) {
            return true;
          }

          const searchable =
            [
              item.video
                .original_filename,
              item.camera?.name,
              item.camera?.location,
              item.latestJob?.id,
              item.jobStatus,
            ]
              .filter(Boolean)
              .join(" ")
              .toLowerCase();

          return searchable.includes(
            normalizedSearch,
          );
        },
      );
    }, [
      processedVideos,
      searchValue,
      statusFilter,
    ]);

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        filteredVideos.length /
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
      filteredVideos.length,
    );

  const paginatedVideos =
    filteredVideos.slice(
      pageStartIndex,
      pageEndIndex,
    );

  const firstVisibleItem =
    filteredVideos.length
      ? pageStartIndex + 1
      : 0;

  const lastVisibleItem =
    filteredVideos.length
      ? pageEndIndex
      : 0;

  const succeededCount =
    processedVideos.filter(
      (item) =>
        item.jobStatus ===
        "succeeded",
    ).length;

  const activeCount =
    processedVideos.filter(
      (item) =>
        item.jobStatus ===
          "queued" ||
        item.jobStatus ===
          "running",
    ).length;

  const failedCount =
    processedVideos.filter(
      (item) =>
        item.jobStatus ===
        "failed",
    ).length;

  function clearFilters() {
    setSearchValue("");
    setStatusFilter("");
    setCurrentPage(1);
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <FileVideo
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Uploaded videos
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {videos.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <CheckCircle2
            size={21}
            className="text-emerald-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Completed
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {succeededCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <RefreshCw
            size={21}
            className="text-amber-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Queued or running
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {activeCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <AlertCircle
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

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Filter
            size={18}
            className="text-cyan-700"
          />

          <h2 className="font-semibold text-slate-950">
            Filter video library
          </h2>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-[1fr_240px_auto]">
          <label className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={searchValue}
              onChange={(event) => {
                setSearchValue(
                  event.target.value,
                );

                setCurrentPage(1);
              }}
              placeholder="Search filename, camera or job ID"
              className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
          </label>

          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(
                event.target.value as
                  | DerivedJobStatus
                  | "",
              );

              setCurrentPage(1);
            }}
            className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-cyan-400"
          >
            <option value="">
              All processing statuses
            </option>

            <option value="not_processed">
              Not Processed
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
            onClick={clearFilters}
            disabled={
              !searchValue &&
              !statusFilter
            }
            className="h-11 w-full rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-600 lg:w-auto hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear
          </button>
        </div>

        <p className="mt-4 text-sm text-slate-500">
          Showing{" "}
          <span className="font-semibold text-slate-900">
            {filteredVideos.length}
          </span>{" "}
          of{" "}
          <span className="font-semibold text-slate-900">
            {videos.length}
          </span>{" "}
          uploaded videos.
        </p>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {filteredVideos.length ? (
          <>
          <MobileTableNotice />

          <div className="overflow-x-auto overscroll-x-contain touch-pan-x [scrollbar-width:thin]">
            <table className="w-full min-w-[1050px] text-left">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4">
                    Video
                  </th>

                  <th className="px-5 py-4">
                    Camera
                  </th>

                  <th className="px-5 py-4">
                    Size
                  </th>

                  <th className="px-5 py-4">
                    Duration
                  </th>

                  <th className="px-5 py-4">
                    Processing
                  </th>

                  <th className="px-5 py-4">
                    Uploaded
                  </th>

                  <th className="px-5 py-4 text-right">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {paginatedVideos.map(
                  ({
                    video,
                    latestJob,
                    jobStatus,
                    camera,
                    fileSize,
                    duration,
                    createdAt,
                  }) => {
                    const StatusIcon =
                      statusIcons[
                        jobStatus
                      ];

                    return (
                      <tr
                        key={video.id}
                        className="hover:bg-slate-50/70"
                      >
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
                              <FileVideo
                                size={19}
                              />
                            </span>

                            <div className="min-w-0">
                              <p className="max-w-[280px] truncate text-sm font-semibold text-slate-950">
                                {
                                  video.original_filename
                                }
                              </p>

                              <p className="mt-1 font-mono text-xs text-slate-400">
                                {video.id.slice(
                                  0,
                                  12,
                                )}
                              </p>
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <p className="text-sm font-medium text-slate-700">
                            {camera?.name ??
                              "Unassigned"}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            {camera?.location ??
                              "No location"}
                          </p>
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-600">
                          {formatFileSize(
                            fileSize,
                          )}
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-600">
                          {formatDuration(
                            duration,
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={[
                              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                              statusStyles[
                                jobStatus
                              ],
                            ].join(" ")}
                          >
                            <StatusIcon
                              size={14}
                              className={
                                jobStatus ===
                                "running"
                                  ? "animate-spin"
                                  : ""
                              }
                            />

                            {formatLabel(
                              jobStatus,
                            )}
                          </span>

                          {latestJob ? (
                            <p className="mt-1 font-mono text-xs text-slate-400">
                              {latestJob.id.slice(
                                0,
                                10,
                              )}
                            </p>
                          ) : null}
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-500">
                          {formatDate(
                            createdAt,
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <div className="flex flex-wrap justify-end gap-2">
                            {latestJob ? (
                              <Link
                                href={`/jobs/${latestJob.id}`}
                                className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 px-3 text-sm font-semibold text-slate-600 hover:border-cyan-300 hover:bg-cyan-50 hover:text-cyan-800"
                              >
                                Job
                              </Link>
                            ) : null}

                            <Link
                              href={`/videos/${video.id}`}
                              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-cyan-500 px-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
                            >
                              <Eye size={16} />
                              Details
                            </Link>

                            <DeleteVideoButton
                              videoId={video.id}
                              disabled={
                                jobStatus ===
                                  "queued" ||
                                jobStatus ===
                                  "running"
                              }
                            />
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
            <FileVideo
              size={36}
              className="mx-auto text-slate-300"
            />

            <h3 className="mt-4 font-semibold text-slate-950">
              No videos found
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              No uploaded videos match the current filters.
            </p>

            <Link
              href="/videos/upload"
              className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 text-sm font-semibold text-slate-950"
            >
              <Upload size={17} />
              Upload video
            </Link>
          </div>
        )}

        {filteredVideos.length ? (
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
              filteredVideos.length
            }
            startItem={
              firstVisibleItem
            }
            endItem={
              lastVisibleItem
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
    </div>
  );
}
