"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  ShieldAlert,
  Video,
  XCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  AnalyticsDashboardData,
} from "@/types/analytics";

type AnalyticsDashboardProps = {
  data: AnalyticsDashboardData;
};

const reviewColors: Record<
  string,
  string
> = {
  pending: "#f59e0b",
  confirmed: "#10b981",
  rejected: "#f43f5e",
};

const jobColors: Record<
  string,
  string
> = {
  queued: "#64748b",
  running: "#f59e0b",
  succeeded: "#10b981",
  failed: "#f43f5e",
  cancelled: "#94a3b8",
};

function formatPercentage(
  value: number | null,
): string {
  if (value === null) {
    return "—";
  }

  return `${Math.round(
    value * 100,
  )}%`;
}

function ChartEmptyState({
  message,
}: {
  message: string;
}) {
  return (
    <div className="flex h-[320px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center text-sm text-slate-400">
      {message}
    </div>
  );
}

export function AnalyticsDashboard({
  data,
}: AnalyticsDashboardProps) {
  const {
    summary,
    violationsByType,
    violationsByReviewStatus,
    jobsByStatus,
    violationTrend,
    cameras,
  } = data;

  const hasTrendData =
    violationTrend.some(
      (point) =>
        point.violations > 0 ||
        point.confirmed > 0 ||
        point.rejected > 0,
    );

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ShieldAlert
            size={22}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Total violations
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {summary.totalViolations}
          </p>

          <p className="mt-2 text-xs text-slate-400">
            {summary.pendingViolations}
            {" "}awaiting review
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Gauge
            size={22}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Average confidence
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {formatPercentage(
              summary.averageConfidence,
            )}
          </p>

          <p className="mt-2 text-xs text-slate-400">
            Across available confidence scores
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Video
            size={22}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Processing success
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {formatPercentage(
              summary.processingSuccessRate,
            )}
          </p>

          <p className="mt-2 text-xs text-slate-400">
            {summary.successfulJobs}
            {" "}successful of{" "}
            {summary.totalJobs} jobs
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Activity
            size={22}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Reviewed violations
          </p>

          <p className="mt-1 text-3xl font-bold text-slate-950">
            {summary.confirmedViolations +
              summary.rejectedViolations}
          </p>

          <div className="mt-2 flex gap-3 text-xs">
            <span className="inline-flex items-center gap-1 text-emerald-600">
              <CheckCircle2 size={13} />
              {summary.confirmedViolations}
            </span>

            <span className="inline-flex items-center gap-1 text-rose-600">
              <XCircle size={13} />
              {summary.rejectedViolations}
            </span>
          </div>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="font-semibold text-slate-950">
              Violations by type
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Frequency of each detected violation category.
            </p>
          </div>

          <div className="mt-5">
            {violationsByType.length ? (
              <ResponsiveContainer
                width="100%"
                height={340}
              >
                <BarChart
                  data={violationsByType}
                  margin={{
                    top: 10,
                    right: 10,
                    left: -15,
                    bottom: 65,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="label"
                    angle={-35}
                    textAnchor="end"
                    interval={0}
                    height={85}
                    tick={{
                      fontSize: 12,
                    }}
                  />

                  <YAxis
                    allowDecimals={false}
                  />

                  <Tooltip />

                  <Bar
                    dataKey="value"
                    name="Violations"
                    fill="#06b6d4"
                    radius={[
                      6,
                      6,
                      0,
                      0,
                    ]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <ChartEmptyState message="No violation data is available." />
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="font-semibold text-slate-950">
              Review status
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Distribution of pending, confirmed, and rejected events.
            </p>
          </div>

          <div className="mt-5">
            {violationsByReviewStatus.length ? (
              <ResponsiveContainer
                width="100%"
                height={340}
              >
                <PieChart>
                  <Pie
                    data={
                      violationsByReviewStatus
                    }
                    dataKey="value"
                    nameKey="label"
                    innerRadius={75}
                    outerRadius={115}
                    paddingAngle={3}
                  >
                    {violationsByReviewStatus.map(
                      (entry) => (
                        <Cell
                          key={entry.key}
                          fill={
                            reviewColors[
                              entry.key
                            ] ??
                            "#64748b"
                          }
                        />
                      ),
                    )}
                  </Pie>

                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <ChartEmptyState message="No review data is available." />
            )}
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <h2 className="font-semibold text-slate-950">
            Fourteen-day violation trend
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Detected, confirmed, and rejected violations by day.
          </p>
        </div>

        <div className="mt-5">
          {hasTrendData ? (
            <ResponsiveContainer
              width="100%"
              height={360}
            >
              <LineChart
              data={violationTrend}
              margin={{
                top: 10,
                right: 20,
                left: -10,
                bottom: 10,
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
              />

              <XAxis
                dataKey="label"
                tick={{
                  fontSize: 12,
                }}
              />

              <YAxis
                allowDecimals={false}
              />

              <Tooltip />
              <Legend />

              <Line
                type="monotone"
                dataKey="violations"
                name="Detected"
                stroke="#06b6d4"
                strokeWidth={3}
                dot={{
                  r: 3,
                }}
              />

              <Line
                type="monotone"
                dataKey="confirmed"
                name="Confirmed"
                stroke="#10b981"
                strokeWidth={2}
              />

              <Line
                type="monotone"
                dataKey="rejected"
                name="Rejected"
                stroke="#f43f5e"
                strokeWidth={2}
              />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <ChartEmptyState message="No violations match the selected date range and filters." />
          )}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="font-semibold text-slate-950">
              Processing jobs
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Current distribution of processing-job states.
            </p>
          </div>

          <div className="mt-5">
            {jobsByStatus.length ? (
              <ResponsiveContainer
                width="100%"
                height={330}
              >
                <PieChart>
                  <Pie
                    data={jobsByStatus}
                    dataKey="value"
                    nameKey="label"
                    innerRadius={65}
                    outerRadius={105}
                    paddingAngle={3}
                  >
                    {jobsByStatus.map(
                      (entry) => (
                        <Cell
                          key={entry.key}
                          fill={
                            jobColors[
                              entry.key
                            ] ??
                            "#64748b"
                          }
                        />
                      ),
                    )}
                  </Pie>

                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <ChartEmptyState message="No job information is available." />
            )}
          </div>
        </article>

        <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-5 py-5">
            <h2 className="font-semibold text-slate-950">
              Violations by camera
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Review workload and confirmed violations for each camera.
            </p>
          </div>

          {cameras.length ? (
            <div className="overflow-x-auto overscroll-x-contain touch-pan-x [scrollbar-width:thin]">
              <table className="w-full min-w-[650px] text-left">
                <thead className="bg-slate-50">
                  <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-5 py-4">
                      Camera
                    </th>

                    <th className="px-5 py-4">
                      Total
                    </th>

                    <th className="px-5 py-4">
                      Pending
                    </th>

                    <th className="px-5 py-4">
                      Confirmed
                    </th>

                    <th className="px-5 py-4">
                      Rejected
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {cameras.map(
                    (camera) => (
                      <tr
                        key={camera.cameraId}
                        className="hover:bg-slate-50/70"
                      >
                        <td className="px-5 py-4">
                          <p className="text-sm font-semibold text-slate-900">
                            {camera.cameraName}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            {camera.location ??
                              "No location"}
                          </p>
                        </td>

                        <td className="px-5 py-4 text-sm font-semibold text-slate-800">
                          {camera.total}
                        </td>

                        <td className="px-5 py-4 text-sm text-amber-600">
                          {camera.pending}
                        </td>

                        <td className="px-5 py-4 text-sm text-emerald-600">
                          {camera.confirmed}
                        </td>

                        <td className="px-5 py-4 text-sm text-rose-600">
                          {camera.rejected}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex min-h-72 flex-col items-center justify-center px-6 text-center">
              <AlertTriangle
                size={34}
                className="text-slate-300"
              />

              <p className="mt-3 text-sm font-medium text-slate-600">
                No camera analytics available
              </p>
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
