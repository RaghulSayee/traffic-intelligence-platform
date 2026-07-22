import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock3,
  FileVideo,
  Gauge,
  Hash,
  MapPin,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import Link from "next/link";

import {
  EvidenceMedia,
} from "@/components/violations/evidence-media";
import {
  ReviewActions,
} from "@/components/violations/review-actions";
import {
  getCameras,
  getVideos,
} from "@/lib/api/resources";
import {
  getViolation,
  getViolationClipUrl,
  getViolationImageUrl,
} from "@/lib/api/violations";
import type {
  ReviewStatus,
  ViolationEvent,
} from "@/types/violations";

export const dynamic = "force-dynamic";

type ViolationDetailsPageProps = {
  params: Promise<{
    violationId: string;
  }>;
};

const statusStyles: Record<
  ReviewStatus,
  string
> = {
  pending:
    "bg-amber-50 text-amber-700",
  confirmed:
    "bg-emerald-50 text-emerald-700",
  rejected:
    "bg-rose-50 text-rose-700",
};

const statusIcons = {
  pending: Clock3,
  confirmed: CheckCircle2,
  rejected: XCircle,
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
  value: string,
): string {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "medium",
    },
  ).format(new Date(value));
}

function formatConfidence(
  value: number | null,
): string {
  if (value === null) {
    return "Not available";
  }

  return `${Math.round(
    value * 100,
  )}%`;
}

export default async function ViolationDetailsPage({
  params,
}: ViolationDetailsPageProps) {
  const { violationId } =
    await params;

  let violation:
    | ViolationEvent
    | null = null;

  let errorMessage:
    | string
    | null = null;

  let cameraName = "Unassigned";
  let cameraLocation =
    "No location available";

  let videoName =
    "Unknown video";

  try {
    violation =
      await getViolation(
        violationId,
      );

    const [
      cameraResponse,
      videoResponse,
    ] = await Promise.all([
      getCameras({
        limit: 100,
      }),
      getVideos({
        limit: 100,
      }),
    ]);

    const camera =
      violation.camera_id
        ? cameraResponse.items.find(
            (item) =>
              item.id ===
              violation?.camera_id,
          )
        : undefined;

    const video =
      videoResponse.items.find(
        (item) =>
          item.id ===
          violation?.video_id,
      );

    if (camera) {
      cameraName = camera.name;
      cameraLocation =
        camera.location ??
        "No location available";
    }

    if (video) {
      videoName =
        video.original_filename;
    }
  } catch (
    requestError
  ) {
    errorMessage =
      requestError instanceof Error
        ? requestError.message
        : "Violation could not be loaded.";
  }

  if (!violation) {
    return (
      <>
        <Link
          href="/violations"
          className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
        >
          <ArrowLeft size={17} />
          Back to violations
        </Link>

        <section className="mt-6 rounded-2xl border border-rose-200 bg-white p-10 text-center shadow-sm">
          <AlertCircle
            size={38}
            className="mx-auto text-rose-500"
          />

          <h1 className="mt-4 text-xl font-bold text-slate-950">
            Violation unavailable
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            {errorMessage}
          </p>
        </section>
      </>
    );
  }

  const StatusIcon =
    statusIcons[
      violation.review_status
    ];

  const imageUrl =
    violation.evidence_image_key
      ? getViolationImageUrl(
          violation.id,
        )
      : null;

  const clipUrl =
    violation.evidence_clip_key
      ? getViolationClipUrl(
          violation.id,
        )
      : null;

  return (
    <>
      <Link
        href="/violations"
        className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
      >
        <ArrowLeft size={17} />
        Back to violations
      </Link>

      <header className="mt-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Violation evidence
          </p>

          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {formatLabel(
              violation.violation_type,
            )}
          </h1>

          <p className="mt-2 break-all font-mono text-xs text-slate-400">
            {violation.id}
          </p>
        </div>

        <span
          className={[
            "inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold",
            statusStyles[
              violation.review_status
            ],
          ].join(" ")}
        >
          <StatusIcon size={17} />

          {formatLabel(
            violation.review_status,
          )}
        </span>
      </header>

      <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Gauge
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Detection confidence
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {formatConfidence(
              violation.detection_confidence,
            )}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ShieldAlert
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Rule confidence
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {formatConfidence(
              violation.rule_confidence,
            )}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Hash
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Frame number
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {violation.frame_number ??
              "Not available"}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Calendar
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Occurred
          </p>

          <p className="mt-1 text-sm font-semibold text-slate-950">
            {formatDate(
              violation.occurred_at,
            )}
          </p>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_0.7fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-5 font-semibold text-slate-950">
            Supporting evidence
          </h2>

          <EvidenceMedia
            imageUrl={imageUrl}
            clipUrl={clipUrl}
          />
        </article>

        <aside className="space-y-6">
          <ReviewActions
            violation={violation}
          />

          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold text-slate-950">
              Event information
            </h2>

            <dl className="mt-5 space-y-5">
              <div>
                <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <MapPin size={14} />
                  Camera
                </dt>

                <dd className="mt-1 text-sm font-medium text-slate-700">
                  {cameraName}
                </dd>

                <dd className="mt-1 text-xs text-slate-400">
                  {cameraLocation}
                </dd>
              </div>

              <div>
                <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <FileVideo size={14} />
                  Source video
                </dt>

                <dd className="mt-1 break-words text-sm text-slate-700">
                  {videoName}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Track ID
                </dt>

                <dd className="mt-1 text-sm text-slate-700">
                  {violation.track_id ??
                    "Not available"}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  License plate
                </dt>

                <dd className="mt-1 text-sm text-slate-700">
                  {violation.license_plate ??
                    "Not detected"}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Event key
                </dt>

                <dd className="mt-1 break-all font-mono text-xs text-slate-500">
                  {violation.event_key}
                </dd>
              </div>
            </dl>

            {violation.processing_job_id ? (
              <Link
                href={`/jobs/${violation.processing_job_id}`}
                className="mt-6 inline-flex h-10 w-full items-center justify-center rounded-xl border border-cyan-200 bg-cyan-50 text-sm font-semibold text-cyan-800 hover:bg-cyan-100"
              >
                Open processing job
              </Link>
            ) : null}
          </article>
        </aside>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Event metadata
          </h2>

          <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-300">
            {JSON.stringify(
              violation.event_metadata,
              null,
              2,
            )}
          </pre>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Detection geometry
          </h2>

          <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-300">
            {JSON.stringify(
              violation.geometry,
              null,
              2,
            )}
          </pre>
        </article>
      </section>
    </>
  );
}
