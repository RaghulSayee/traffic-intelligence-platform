import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock3,
  Database,
  FileVideo,
  Gauge,
  MapPin,
  PlayCircle,
  XCircle,
} from "lucide-react";
import Link from "next/link";

import {
  getCameras,
  getProcessingJobs,
  getVideos,
} from "@/lib/api/resources";
import type {
  ProcessingJob,
  Video,
} from "@/types/api";

export const dynamic = "force-dynamic";

type VideoDetailsPageProps = {
  params: Promise<{
    videoId: string;
  }>;
};

type CameraRecord = {
  id: string;
  name: string;
  location: string | null;
};

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
      timeStyle: "medium",
    },
  ).format(date);
}

function formatFileSize(
  value: number | null,
): string {
  if (
    value === null ||
    !Number.isFinite(value)
  ) {
    return "Not available";
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
    !Number.isFinite(value)
  ) {
    return "Not available";
  }

  const seconds =
    Math.round(value);

  const minutes =
    Math.floor(seconds / 60);

  const remainingSeconds =
    seconds % 60;

  return minutes > 0
    ? `${minutes}m ${remainingSeconds}s`
    : `${remainingSeconds}s`;
}

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

const jobStatusStyles:
  Record<string, string> = {
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

const jobStatusIcons = {
  queued: Clock3,
  running: Clock3,
  succeeded: CheckCircle2,
  failed: XCircle,
  cancelled: XCircle,
};

export default async function VideoDetailsPage({
  params,
}: VideoDetailsPageProps) {
  const { videoId } =
    await params;

  let video: Video | undefined;
  let videoJobs:
    ProcessingJob[] = [];

  let camera:
    CameraRecord | undefined;

  let loadError:
    string | null = null;

  try {
    const [
      videoResponse,
      jobResponse,
      cameraResponse,
    ] = await Promise.all([
      getVideos({
        limit: 100,
      }),
      getProcessingJobs({
        limit: 100,
      }),
      getCameras({
        limit: 100,
      }),
    ]);

    video =
      videoResponse.items.find(
        (item) =>
          item.id === videoId,
      );

    videoJobs =
      jobResponse.items
        .filter(
          (job) =>
            job.video_id ===
            videoId,
        )
        .sort(
          (first, second) =>
            new Date(
              second.created_at,
            ).getTime() -
            new Date(
              first.created_at,
            ).getTime(),
        );

    if (video) {
      const cameraId =
        getStringField(
          video,
          [
            "camera_id",
            "cameraId",
          ],
        );

      camera =
        cameraId
          ? cameraResponse.items.find(
              (item) =>
                item.id ===
                cameraId,
            )
          : undefined;
    }
  } catch (
    error
  ) {
    loadError =
      error instanceof Error
        ? error.message
        : "Video could not be loaded.";
  }

  if (!video) {
    return (
      <>
        <Link
          href="/videos"
          className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
        >
          <ArrowLeft size={17} />
          Back to videos
        </Link>

        <section className="mt-6 rounded-2xl border border-rose-200 bg-white p-10 text-center shadow-sm">
          <AlertCircle
            size={38}
            className="mx-auto text-rose-500"
          />

          <h1 className="mt-4 text-xl font-bold text-slate-950">
            Video unavailable
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            {loadError ??
              "The requested video was not found."}
          </p>
        </section>
      </>
    );
  }

  const metadata =
    asRecord(video);

  const fileSize =
    getNumberField(
      metadata,
      [
        "file_size_bytes",
        "size_bytes",
        "file_size",
      ],
    );

  const duration =
    getNumberField(
      metadata,
      [
        "duration_seconds",
        "duration",
      ],
    );

  const width =
    getNumberField(
      metadata,
      [
        "width",
        "video_width",
      ],
    );

  const height =
    getNumberField(
      metadata,
      [
        "height",
        "video_height",
      ],
    );

  const frameRate =
    getNumberField(
      metadata,
      [
        "fps",
        "frame_rate",
      ],
    );

  const frameCount =
    getNumberField(
      metadata,
      [
        "frame_count",
        "total_frames",
      ],
    );

  const contentType =
    getStringField(
      metadata,
      [
        "content_type",
        "mime_type",
      ],
    );

  const createdAt =
    getStringField(
      metadata,
      [
        "created_at",
        "uploaded_at",
      ],
    );

  const latestJob =
    videoJobs[0];

  return (
    <>
      <Link
        href="/videos"
        className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
      >
        <ArrowLeft size={17} />
        Back to videos
      </Link>

      <header className="mt-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Video details
          </p>

          <h1 className="mt-2 break-words text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {video.original_filename}
          </h1>

          <p className="mt-2 break-all font-mono text-xs text-slate-400">
            {video.id}
          </p>
        </div>

        {latestJob ? (
          <Link
            href={`/jobs/${latestJob.id}`}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
          >
            <PlayCircle size={18} />
            Open latest job
          </Link>
        ) : null}
      </header>

      <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Database
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            File size
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {formatFileSize(
              fileSize,
            )}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Clock3
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Duration
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {formatDuration(
              duration,
            )}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Gauge
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Resolution
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {width !== null &&
            height !== null
              ? `${width} × ${height}`
              : "Not available"}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Calendar
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Uploaded
          </p>

          <p className="mt-1 text-sm font-semibold text-slate-950">
            {formatDate(
              createdAt,
            )}
          </p>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Source information
          </h2>

          <dl className="mt-5 space-y-5">
            <div>
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <MapPin size={14} />
                Camera
              </dt>

              <dd className="mt-1 text-sm font-medium text-slate-700">
                {camera?.name ??
                  "Unassigned"}
              </dd>

              <dd className="mt-1 text-xs text-slate-400">
                {camera?.location ??
                  "No location available"}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Content type
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {contentType ??
                  "Not available"}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Frame rate
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {frameRate !== null
                  ? `${frameRate.toFixed(
                      2,
                    )} FPS`
                  : "Not available"}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Frame count
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {frameCount ??
                  "Not available"}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Processing jobs
              </dt>

              <dd className="mt-1 text-sm text-slate-700">
                {videoJobs.length}
              </dd>
            </div>
          </dl>
        </article>

        <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-5 py-5">
            <h2 className="font-semibold text-slate-950">
              Processing history
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Every analysis job created for this video.
            </p>
          </div>

          {videoJobs.length ? (
            <div className="divide-y divide-slate-100">
              {videoJobs.map(
                (job) => {
                  const StatusIcon =
                    jobStatusIcons[
                      job.status as keyof typeof jobStatusIcons
                    ] ?? Clock3;

                  return (
                    <div
                      key={job.id}
                      className="flex flex-col justify-between gap-4 px-5 py-4 sm:flex-row sm:items-center"
                    >
                      <div className="flex items-start gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
                          <StatusIcon
                            size={18}
                          />
                        </span>

                        <div>
                          <p className="text-sm font-semibold text-slate-950">
                            {formatLabel(
                              job.status,
                            )}
                          </p>

                          <p className="mt-1 font-mono text-xs text-slate-400">
                            {job.id}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            Created{" "}
                            {formatDate(
                              job.created_at,
                            )}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={[
                            "rounded-full px-3 py-1 text-xs font-semibold",
                            jobStatusStyles[
                              job.status
                            ] ??
                              "bg-slate-100 text-slate-600",
                          ].join(" ")}
                        >
                          {Math.round(
                            job.progress_percent,
                          )}
                          %
                        </span>

                        <Link
                          href={`/jobs/${job.id}`}
                          className="inline-flex h-9 items-center justify-center rounded-lg border border-cyan-200 bg-cyan-50 px-3 text-sm font-semibold text-cyan-800 hover:bg-cyan-100"
                        >
                          View job
                        </Link>
                      </div>
                    </div>
                  );
                },
              )}
            </div>
          ) : (
            <div className="px-6 py-16 text-center">
              <FileVideo
                size={34}
                className="mx-auto text-slate-300"
              />

              <h3 className="mt-4 font-semibold text-slate-950">
                No processing jobs
              </h3>

              <p className="mt-2 text-sm text-slate-500">
                No analysis job is associated with this video.
              </p>
            </div>
          )}
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-slate-950">
          Raw video metadata
        </h2>

        <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-300">
          {JSON.stringify(
            video,
            null,
            2,
          )}
        </pre>
      </section>
    </>
  );
}
