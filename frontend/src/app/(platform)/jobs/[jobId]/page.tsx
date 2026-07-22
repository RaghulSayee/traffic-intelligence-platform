import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
} from "lucide-react";
import Link from "next/link";

import {
  getProcessingJob,
  getProcessingJobPreviewUrl,
} from "@/lib/api/resources";
import type {
  ProcessingJob,
} from "@/types/api";

export const dynamic = "force-dynamic";

type JobDetailsPageProps = {
  params: Promise<{
    jobId: string;
  }>;
};

function formatDate(
  value: string | null,
): string {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "medium",
    },
  ).format(new Date(value));
}

export default async function JobDetailsPage({
  params,
}: JobDetailsPageProps) {
  const { jobId } = await params;

  let job: ProcessingJob | null = null;
  let errorMessage: string | null = null;

  try {
    job =
      await getProcessingJob(jobId);
  } catch (error) {
    errorMessage =
      error instanceof Error
        ? error.message
        : "The processing job could not be loaded.";
  }

  if (!job) {
    return (
      <>
        <Link
          href="/jobs"
          className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
        >
          <ArrowLeft size={17} />
          Back to jobs
        </Link>

        <section className="mt-6 rounded-2xl border border-rose-200 bg-white p-10 text-center shadow-sm">
          <AlertCircle
            size={38}
            className="mx-auto text-rose-500"
          />

          <h1 className="mt-4 text-xl font-bold text-slate-950">
            Job unavailable
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            {errorMessage}
          </p>
        </section>
      </>
    );
  }

  const previewUrl =
    getProcessingJobPreviewUrl(
      job.id,
    );

  const succeeded =
    job.status === "succeeded";

  return (
    <>
      <Link
        href="/jobs"
        className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
      >
        <ArrowLeft size={17} />
        Back to jobs
      </Link>

      <header className="mt-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Processing job
          </p>

          <h1 className="mt-2 text-2xl font-bold text-slate-950">
            Job details
          </h1>

          <p className="mt-2 break-all font-mono text-xs text-slate-400">
            {job.id}
          </p>
        </div>

        <span
          className={[
            "inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold",
            succeeded
              ? "bg-emerald-50 text-emerald-700"
              : "bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          {succeeded ? (
            <CheckCircle2 size={17} />
          ) : (
            <Clock3 size={17} />
          )}

          {job.status}
        </span>
      </header>

      <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">
            Progress
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-950">
            {Math.round(
              job.progress_percent,
            )}
            %
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">
            Last processed frame
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-950">
            {job.last_processed_frame}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">
            Pipeline version
          </p>

          <p className="mt-2 text-xl font-bold text-slate-950">
            {job.pipeline_version ??
              "Not available"}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">
            Attempts
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-950">
            {job.attempt_count}
          </p>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold text-slate-950">
            Annotated preview
          </h2>

          {succeeded ? (
            <video
              controls
              preload="metadata"
              src={previewUrl}
              className="aspect-video w-full rounded-xl bg-black"
            >
              Your browser does not support
              video playback.
            </video>
          ) : (
            <div className="flex aspect-video items-center justify-center rounded-xl bg-slate-950 text-sm text-slate-400">
              Preview becomes available after
              processing completes.
            </div>
          )}
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Job timeline
          </h2>

          <dl className="mt-5 space-y-5 text-sm">
            <div>
              <dt className="text-xs font-semibold uppercase text-slate-400">
                Created
              </dt>

              <dd className="mt-1 text-slate-700">
                {formatDate(
                  job.created_at,
                )}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase text-slate-400">
                Started
              </dt>

              <dd className="mt-1 text-slate-700">
                {formatDate(
                  job.started_at,
                )}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-semibold uppercase text-slate-400">
                Completed
              </dt>

              <dd className="mt-1 text-slate-700">
                {formatDate(
                  job.completed_at,
                )}
              </dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-slate-950">
          Pipeline metrics
        </h2>

        <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-300">
          {JSON.stringify(
            job.job_metrics ?? {},
            null,
            2,
          )}
        </pre>
      </section>
    </>
  );
}
