import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileVideo,
  ShieldAlert,
  Upload,
} from "lucide-react";

import {
  LiveRefreshControl,
} from "@/components/ui/live-refresh-control";
import { PageHeader } from "@/components/ui/page-header";
import { getDashboardData } from "@/lib/api/dashboard";

export const dynamic = "force-dynamic";

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
  value: string,
): string {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(value));
}

function getConfidence(
  detectionConfidence: number | null,
  ruleConfidence: number | null,
): string {
  const confidence = Math.max(
    detectionConfidence ?? 0,
    ruleConfidence ?? 0,
  );

  return confidence > 0
    ? `${Math.round(confidence * 100)}%`
    : "—";
}

const jobStatusStyles = {
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

export default async function DashboardPage() {
  const data = await getDashboardData();

  const videosById = new Map(
    data.videos.items.map((video) => [
      video.id,
      video,
    ]),
  );

  const camerasById = new Map(
    data.cameras.items.map((camera) => [
      camera.id,
      camera,
    ]),
  );

  const statistics = [
    {
      label: "Uploaded videos",
      value: data.videos.total,
      detail: "Traffic videos registered",
      icon: FileVideo,
    },
    {
      label: "Violations detected",
      value: data.violations.total,
      detail: `${data.pendingViolationCount} awaiting review`,
      icon: ShieldAlert,
    },
    {
      label: "Active jobs",
      value: data.activeJobCount,
      detail: "Queued and processing",
      icon: Clock,
    },
    {
      label: "Completed jobs",
      value: data.completedJobCount,
      detail: "Successfully processed",
      icon: CheckCircle2,
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="System overview"
        title="Traffic monitoring dashboard"
        description="Live processing activity and violation information from the FastAPI backend."
        action={
          <div className="flex flex-wrap items-center justify-end gap-3">
            <LiveRefreshControl
              intervalMs={5000}
            />

            <Link
              href="/videos/upload"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
            >
              <Upload size={18} />
              Upload video
            </Link>
          </div>
        }
      />

      {!data.dataAvailable ? (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Some dashboard data could not be loaded.
          Confirm that FastAPI and PostgreSQL are
          running.
        </div>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statistics.map((statistic) => {
          const Icon = statistic.icon;

          return (
            <article
              key={statistic.label}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
                <Icon size={21} />
              </span>

              <p className="mt-5 text-sm font-medium text-slate-500">
                {statistic.label}
              </p>

              <p className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
                {statistic.value}
              </p>

              <p className="mt-2 text-xs text-slate-400">
                {statistic.detail}
              </p>
            </article>
          );
        })}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <h3 className="font-semibold text-slate-950">
                Recent processing jobs
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Latest backend processing activity
              </p>
            </div>

            <Link
              href="/jobs"
              className="text-sm font-semibold text-cyan-700"
            >
              View all
            </Link>
          </div>

          {data.recentJobs.items.length ? (
            <div className="divide-y divide-slate-100">
              {data.recentJobs.items.map(
                (job) => {
                  const video =
                    videosById.get(
                      job.video_id,
                    );

                  return (
                    <div
                      key={job.id}
                      className="px-5 py-4"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            {video?.original_filename ??
                              `Video ${job.video_id.slice(0, 8)}`}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            {job.pipeline_version
                              ? `Pipeline ${job.pipeline_version}`
                              : job.pipeline_name}
                          </p>
                        </div>

                        <span
                          className={[
                            "rounded-full px-3 py-1 text-xs font-semibold",
                            jobStatusStyles[
                              job.status
                            ],
                          ].join(" ")}
                        >
                          {formatLabel(
                            job.status,
                          )}
                        </span>
                      </div>

                      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-cyan-500"
                          style={{
                            width: `${Math.min(
                              Math.max(
                                job.progress_percent,
                                0,
                              ),
                              100,
                            )}%`,
                          }}
                        />
                      </div>

                      <p className="mt-2 text-right text-xs text-slate-400">
                        {Math.round(
                          job.progress_percent,
                        )}
                        %
                      </p>
                    </div>
                  );
                },
              )}
            </div>
          ) : (
            <p className="px-5 py-10 text-center text-sm text-slate-500">
              No processing jobs found.
            </p>
          )}
        </article>

        <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <h3 className="font-semibold text-slate-950">
                Recent violations
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Latest detected events
              </p>
            </div>

            <Link
              href="/violations"
              className="text-sm font-semibold text-cyan-700"
            >
              Review all
            </Link>
          </div>

          {data.violations.items.length ? (
            <div className="divide-y divide-slate-100">
              {data.violations.items.map(
                (violation) => {
                  const camera =
                    violation.camera_id
                      ? camerasById.get(
                          violation.camera_id,
                        )
                      : undefined;

                  return (
                    <div
                      key={violation.id}
                      className="flex gap-3 px-5 py-4"
                    >
                      <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
                        <AlertTriangle
                          size={19}
                        />
                      </span>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-slate-900">
                            {formatLabel(
                              violation.violation_type,
                            )}
                          </p>

                          <span className="text-xs font-medium text-emerald-700">
                            {getConfidence(
                              violation.detection_confidence,
                              violation.rule_confidence,
                            )}
                          </span>
                        </div>

                        <p className="mt-1 truncate text-xs text-slate-500">
                          {camera?.name ??
                            camera?.location ??
                            "Uploaded video"}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          {formatDate(
                            violation.occurred_at,
                          )}
                        </p>
                      </div>
                    </div>
                  );
                },
              )}
            </div>
          ) : (
            <p className="px-5 py-10 text-center text-sm text-slate-500">
              No violations detected yet.
            </p>
          )}
        </article>
      </section>

      <section className="mt-6 rounded-2xl bg-slate-950 p-6 text-white shadow-sm">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-semibold text-cyan-400">
              Backend status
            </p>

            <h3 className="mt-2 text-xl font-bold">
              {data.backendOnline
                ? "Traffic Intelligence API is operational"
                : "Traffic Intelligence API is unavailable"}
            </h3>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              {data.backendOnline
                ? "Dashboard values are loaded from the FastAPI service."
                : "Start the backend server on port 8000 to load live data."}
            </p>
          </div>

          <span
            className={[
              "inline-flex w-fit items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold",
              data.backendOnline
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "border-rose-500/30 bg-rose-500/10 text-rose-300",
            ].join(" ")}
          >
            <span
              className={[
                "h-2.5 w-2.5 rounded-full",
                data.backendOnline
                  ? "bg-emerald-400"
                  : "bg-rose-400",
              ].join(" ")}
            />

            {data.backendOnline
              ? "Operational"
              : "Offline"}
          </span>
        </div>
      </section>
    </>
  );
}
