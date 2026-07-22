import {
  AlertCircle,
  ArrowLeft,
  Camera as CameraIcon,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileVideo,
  Layers3,
  MapPin,
  Route,
  ShieldAlert,
  Signpost,
  Upload,
  Zap,
} from "lucide-react";
import Link from "next/link";

import {
  SceneReadinessPanel,
} from "@/components/cameras/scene-readiness-panel";
import {
  getCamera,
  getCameraScene,
} from "@/lib/api/cameras";
import {
  getViolations,
} from "@/lib/api/violations";
import {
  getEnabledSceneReadiness,
} from "@/lib/cameras/scene-readiness";
import type {
  Camera,
} from "@/types/cameras";
import type {
  CameraSceneConfiguration,
} from "@/types/camera-scene";
import type {
  ViolationEvent,
} from "@/types/violations";

export const dynamic = "force-dynamic";

type CameraTestPageProps = {
  params: Promise<{
    cameraId: string;
  }>;
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

function formatConfidence(
  violation: ViolationEvent,
): string {
  const values = [
    violation.detection_confidence,
    violation.rule_confidence,
    violation.ocr_confidence,
  ].filter(
    (value): value is number =>
      typeof value === "number" &&
      Number.isFinite(value),
  );

  if (!values.length) {
    return "—";
  }

  return `${Math.round(
    Math.max(...values) * 100,
  )}%`;
}

const reviewStyles = {
  pending:
    "bg-amber-50 text-amber-700",
  confirmed:
    "bg-emerald-50 text-emerald-700",
  rejected:
    "bg-rose-50 text-rose-700",
};

export default async function CameraTestPage({
  params,
}: CameraTestPageProps) {
  const { cameraId } =
    await params;

  let camera:
    | Camera
    | null = null;

  let scene:
    | CameraSceneConfiguration
    | null = null;

  let violations:
    ViolationEvent[] = [];

  let totalViolations = 0;

  let errorMessage:
    | string
    | null = null;

  try {
    const [
      cameraResponse,
      sceneResponse,
      violationResponse,
    ] = await Promise.all([
      getCamera(cameraId),
      getCameraScene(cameraId),
      getViolations({
        cameraId,
        limit: 100,
      }),
    ]);

    camera = cameraResponse;
    scene = sceneResponse;
    violations =
      violationResponse.items;
    totalViolations =
      violationResponse.total;
  } catch (error) {
    errorMessage =
      error instanceof Error
        ? error.message
        : "Camera test information could not be loaded.";
  }

  if (!camera || !scene) {
    return (
      <>
        <Link
          href="/cameras"
          className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
        >
          <ArrowLeft size={17} />
          Back to cameras
        </Link>

        <section className="mt-6 rounded-2xl border border-rose-200 bg-white p-10 text-center shadow-sm">
          <AlertCircle
            size={38}
            className="mx-auto text-rose-500"
          />

          <h1 className="mt-4 text-xl font-bold text-slate-950">
            Test center unavailable
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            {errorMessage}
          </p>
        </section>
      </>
    );
  }

  const readiness =
    getEnabledSceneReadiness(
      scene,
    );

  const readyCount =
    readiness.filter(
      (rule) => rule.ready,
    ).length;

  const blockedCount =
    readiness.length -
    readyCount;

  const pendingCount =
    violations.filter(
      (violation) =>
        violation.review_status ===
        "pending",
    ).length;

  const recentViolations =
    [...violations]
      .sort(
        (first, second) =>
          new Date(
            second.occurred_at,
          ).getTime() -
          new Date(
            first.occurred_at,
          ).getTime(),
      )
      .slice(0, 10);

  return (
    <>
      <Link
        href={`/cameras/${camera.id}/scene`}
        className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
      >
        <ArrowLeft size={17} />
        Back to scene editor
      </Link>

      <header className="mt-5 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Scene testing
          </p>

          <h1 className="mt-2 flex items-center gap-3 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            <CameraIcon
              size={29}
              className="text-cyan-700"
            />

            {camera.name}
          </h1>

          <p className="mt-2 flex items-center gap-2 text-sm text-slate-500">
            <MapPin size={15} />

            {camera.location ??
              "No location configured"}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link
            href={`/cameras/${camera.id}/scene`}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Layers3 size={18} />
            Edit scene
          </Link>

          <Link
            href="/videos/upload"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
          >
            <Upload size={18} />
            Upload test video
          </Link>
        </div>
      </header>

      <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ShieldAlert
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Enabled rules
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {readiness.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <CheckCircle2
            size={21}
            className="text-emerald-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Rules ready
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {readyCount}
          </p>

          <p className="mt-2 text-xs text-slate-400">
            {blockedCount} need setup
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Zap
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Camera violations
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {totalViolations}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Clock3
            size={21}
            className="text-amber-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Pending review
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {pendingCount}
          </p>
        </article>
      </section>

      <div className="mt-6">
        <SceneReadinessPanel
          scene={scene}
        />
      </div>

      <section className="mt-6 grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Scene geometry
          </h2>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <Layers3
                size={18}
                className="text-cyan-700"
              />

              <p className="mt-3 text-xs text-slate-500">
                Monitoring zone
              </p>

              <p className="mt-1 font-semibold text-slate-900">
                {scene.monitoring_zone
                  ? "Configured"
                  : "Missing"}
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <Route
                size={18}
                className="text-cyan-700"
              />

              <p className="mt-3 text-xs text-slate-500">
                Lanes
              </p>

              <p className="mt-1 font-semibold text-slate-900">
                {scene.lanes.length}
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <Zap
                size={18}
                className="text-rose-600"
              />

              <p className="mt-3 text-xs text-slate-500">
                Traffic signals
              </p>

              <p className="mt-1 font-semibold text-slate-900">
                {
                  scene
                    .traffic_light_regions
                    .length
                }
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <Signpost
                size={18}
                className="text-amber-600"
              />

              <p className="mt-3 text-xs text-slate-500">
                Stop lines
              </p>

              <p className="mt-1 font-semibold text-slate-900">
                {scene.stop_lines.length}
              </p>
            </div>
          </div>

          <h3 className="mt-6 text-sm font-semibold text-slate-900">
            Enabled violations
          </h3>

          <div className="mt-3 flex flex-wrap gap-2">
            {scene.enabled_violations.length ? (
              scene.enabled_violations.map(
                (violation) => (
                  <span
                    key={violation}
                    className="rounded-full bg-cyan-50 px-3 py-1.5 text-xs font-semibold text-cyan-800"
                  >
                    {formatLabel(
                      violation,
                    )}
                  </span>
                ),
              )
            ) : (
              <p className="text-sm text-slate-400">
                No violation rules enabled.
              </p>
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Test workflow
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Process footage using this camera
            and inspect the generated results.
          </p>

          <ol className="mt-5 space-y-4">
            <li className="flex gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-sm font-bold text-cyan-800">
                1
              </span>

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Confirm scene readiness
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  Every enabled rule should
                  show Ready before testing.
                </p>
              </div>
            </li>

            <li className="flex gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-sm font-bold text-cyan-800">
                2
              </span>

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Upload test footage
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  Select this camera in the
                  upload form so its scene
                  configuration is used.
                </p>
              </div>
            </li>

            <li className="flex gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-sm font-bold text-cyan-800">
                3
              </span>

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Wait for processing
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  Open the processing job and
                  verify that it reaches
                  Succeeded.
                </p>
              </div>
            </li>

            <li className="flex gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-sm font-bold text-cyan-800">
                4
              </span>

              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Review violations
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  Inspect evidence, confidence,
                  tracking metadata, and rule
                  results.
                </p>
              </div>
            </li>
          </ol>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <Link
              href="/videos/upload"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
            >
              <Upload size={17} />
              Upload
            </Link>

            <Link
              href="/jobs"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <FileVideo size={17} />
              Jobs
            </Link>

            <Link
              href="/violations"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <ShieldAlert size={17} />
              Violations
            </Link>
          </div>
        </article>
      </section>

      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-3 border-b border-slate-200 px-5 py-5 sm:flex-row sm:items-center">
          <div>
            <h2 className="font-semibold text-slate-950">
              Recent camera violations
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Latest detected events associated
              with this camera.
            </p>
          </div>

          <Link
            href="/violations"
            className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
          >
            View all
            <ExternalLink size={15} />
          </Link>
        </div>

        {recentViolations.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left">
              <thead className="bg-slate-50">
                <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4">
                    Violation
                  </th>

                  <th className="px-5 py-4">
                    Confidence
                  </th>

                  <th className="px-5 py-4">
                    Review
                  </th>

                  <th className="px-5 py-4">
                    Occurred
                  </th>

                  <th className="px-5 py-4 text-right">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {recentViolations.map(
                  (violation) => (
                    <tr
                      key={violation.id}
                      className="hover:bg-slate-50/70"
                    >
                      <td className="px-5 py-4">
                        <p className="text-sm font-semibold text-slate-950">
                          {formatLabel(
                            violation.violation_type,
                          )}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          Frame{" "}
                          {violation.frame_number ??
                            "—"}
                        </p>
                      </td>

                      <td className="px-5 py-4 text-sm font-semibold text-cyan-700">
                        {formatConfidence(
                          violation,
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={[
                            "rounded-full px-3 py-1 text-xs font-semibold capitalize",
                            reviewStyles[
                              violation.review_status
                            ],
                          ].join(" ")}
                        >
                          {
                            violation.review_status
                          }
                        </span>
                      </td>

                      <td className="px-5 py-4 text-sm text-slate-500">
                        {formatDate(
                          violation.occurred_at,
                        )}
                      </td>

                      <td className="px-5 py-4 text-right">
                        <Link
                          href={`/violations/${violation.id}`}
                          className="inline-flex h-9 items-center justify-center rounded-lg border border-cyan-200 bg-cyan-50 px-3 text-sm font-semibold text-cyan-800 hover:bg-cyan-100"
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-16 text-center">
            <ShieldAlert
              size={36}
              className="mx-auto text-slate-300"
            />

            <h3 className="mt-4 font-semibold text-slate-950">
              No camera violations yet
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              Upload and process a test video
              assigned to this camera.
            </p>
          </div>
        )}
      </section>
    </>
  );
}
