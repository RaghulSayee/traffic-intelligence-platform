"use client";

import {
  CalendarDays,
  Filter,
  RotateCcw,
  SlidersHorizontal,
} from "lucide-react";
import {
  useMemo,
  useState,
} from "react";

import {
  AnalyticsDashboard,
} from "@/components/analytics/analytics-dashboard";
import {
  buildAnalyticsDashboardData,
} from "@/lib/analytics/build-dashboard-data";
import type {
  ProcessingJob,
} from "@/types/api";
import type {
  ReviewStatus,
  ViolationEvent,
  ViolationType,
} from "@/types/violations";

type CameraRecord = {
  id: string;
  name: string;
  location: string | null;
};

type AnalyticsExplorerProps = {
  violations: ViolationEvent[];
  jobs: ProcessingJob[];
  cameras: CameraRecord[];
};

const violationTypes: Array<{
  value: ViolationType;
  label: string;
}> = [
  {
    value: "no_helmet",
    label: "No Helmet",
  },
  {
    value: "triple_riding",
    label: "Triple Riding",
  },
  {
    value: "red_light",
    label: "Red Light",
  },
  {
    value: "wrong_way",
    label: "Wrong Way",
  },
  {
    value: "lane_violation",
    label: "Lane Violation",
  },
  {
    value: "illegal_parking",
    label: "Illegal Parking",
  },
  {
    value: "speeding",
    label: "Speeding",
  },
  {
    value: "mobile_phone",
    label: "Mobile Phone",
  },
  {
    value: "seatbelt",
    label: "Seatbelt",
  },
];

const reviewStatuses: Array<{
  value: ReviewStatus;
  label: string;
}> = [
  {
    value: "pending",
    label: "Pending",
  },
  {
    value: "confirmed",
    label: "Confirmed",
  },
  {
    value: "rejected",
    label: "Rejected",
  },
];

function isDateWithinRange(
  value: string,
  fromDate: string,
  toDate: string,
): boolean {
  const timestamp =
    new Date(value).getTime();

  if (Number.isNaN(timestamp)) {
    return false;
  }

  if (fromDate) {
    const startTimestamp =
      new Date(
        `${fromDate}T00:00:00`,
      ).getTime();

    if (
      !Number.isNaN(startTimestamp) &&
      timestamp < startTimestamp
    ) {
      return false;
    }
  }

  if (toDate) {
    const endTimestamp =
      new Date(
        `${toDate}T23:59:59.999`,
      ).getTime();

    if (
      !Number.isNaN(endTimestamp) &&
      timestamp > endTimestamp
    ) {
      return false;
    }
  }

  return true;
}

export function AnalyticsExplorer({
  violations,
  jobs,
  cameras,
}: AnalyticsExplorerProps) {
  const [
    fromDate,
    setFromDate,
  ] = useState("");

  const [
    toDate,
    setToDate,
  ] = useState("");

  const [
    selectedViolationType,
    setSelectedViolationType,
  ] = useState<
    ViolationType | ""
  >("");

  const [
    selectedReviewStatus,
    setSelectedReviewStatus,
  ] = useState<
    ReviewStatus | ""
  >("");

  const [
    selectedCameraId,
    setSelectedCameraId,
  ] = useState("");

  const filteredViolations =
    useMemo(() => {
      return violations.filter(
        (violation) => {
          if (
            selectedViolationType &&
            violation.violation_type !==
              selectedViolationType
          ) {
            return false;
          }

          if (
            selectedReviewStatus &&
            violation.review_status !==
              selectedReviewStatus
          ) {
            return false;
          }

          if (
            selectedCameraId &&
            violation.camera_id !==
              selectedCameraId
          ) {
            return false;
          }

          return isDateWithinRange(
            violation.occurred_at,
            fromDate,
            toDate,
          );
        },
      );
    }, [
      violations,
      selectedViolationType,
      selectedReviewStatus,
      selectedCameraId,
      fromDate,
      toDate,
    ]);

  const filteredJobs =
    useMemo(() => {
      return jobs.filter((job) =>
        isDateWithinRange(
          job.created_at,
          fromDate,
          toDate,
        ),
      );
    }, [
      jobs,
      fromDate,
      toDate,
    ]);

  const filteredCameras =
    useMemo(() => {
      if (!selectedCameraId) {
        return cameras;
      }

      return cameras.filter(
        (camera) =>
          camera.id ===
          selectedCameraId,
      );
    }, [
      cameras,
      selectedCameraId,
    ]);

  const analyticsData =
    useMemo(
      () =>
        buildAnalyticsDashboardData({
          violations:
            filteredViolations,
          jobs: filteredJobs,
          cameras:
            filteredCameras,
        }),
      [
        filteredViolations,
        filteredJobs,
        filteredCameras,
      ],
    );

  const activeFilterCount = [
    fromDate,
    toDate,
    selectedViolationType,
    selectedReviewStatus,
    selectedCameraId,
  ].filter(Boolean).length;

  function resetFilters() {
    setFromDate("");
    setToDate("");
    setSelectedViolationType("");
    setSelectedReviewStatus("");
    setSelectedCameraId("");
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
              <SlidersHorizontal
                size={21}
              />
            </span>

            <div>
              <h2 className="font-semibold text-slate-950">
                Analytics filters
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Refine charts by time,
                violation, review status, and
                camera.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
              <Filter size={14} />

              {activeFilterCount}
              {" "}
              active
            </span>

            <button
              type="button"
              onClick={resetFilters}
              disabled={
                activeFilterCount === 0
              }
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label>
            <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <CalendarDays size={14} />
              From date
            </span>

            <input
              type="date"
              value={fromDate}
              max={toDate || undefined}
              onChange={(event) =>
                setFromDate(
                  event.target.value,
                )
              }
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
          </label>

          <label>
            <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <CalendarDays size={14} />
              To date
            </span>

            <input
              type="date"
              value={toDate}
              min={
                fromDate || undefined
              }
              onChange={(event) =>
                setToDate(
                  event.target.value,
                )
              }
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
          </label>

          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Violation type
            </span>

            <select
              value={
                selectedViolationType
              }
              onChange={(event) =>
                setSelectedViolationType(
                  event.target.value as
                    | ViolationType
                    | "",
                )
              }
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-cyan-400"
            >
              <option value="">
                All violation types
              </option>

              {violationTypes.map(
                (type) => (
                  <option
                    key={type.value}
                    value={type.value}
                  >
                    {type.label}
                  </option>
                ),
              )}
            </select>
          </label>

          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Review status
            </span>

            <select
              value={
                selectedReviewStatus
              }
              onChange={(event) =>
                setSelectedReviewStatus(
                  event.target.value as
                    | ReviewStatus
                    | "",
                )
              }
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-cyan-400"
            >
              <option value="">
                All review statuses
              </option>

              {reviewStatuses.map(
                (status) => (
                  <option
                    key={status.value}
                    value={status.value}
                  >
                    {status.label}
                  </option>
                ),
              )}
            </select>
          </label>

          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Camera
            </span>

            <select
              value={selectedCameraId}
              onChange={(event) =>
                setSelectedCameraId(
                  event.target.value,
                )
              }
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-cyan-400"
            >
              <option value="">
                All cameras
              </option>

              {cameras.map(
                (camera) => (
                  <option
                    key={camera.id}
                    value={camera.id}
                  >
                    {camera.name}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>

        <div className="mt-5 flex flex-col justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3 text-sm sm:flex-row sm:items-center">
          <p className="text-slate-600">
            Showing{" "}
            <span className="font-semibold text-slate-950">
              {filteredViolations.length}
            </span>{" "}
            of{" "}
            <span className="font-semibold text-slate-950">
              {violations.length}
            </span>{" "}
            loaded violations.
          </p>

          <p className="text-slate-500">
            Processing jobs in range:{" "}
            <span className="font-semibold text-slate-800">
              {filteredJobs.length}
            </span>
          </p>
        </div>
      </section>

      <AnalyticsDashboard
        data={analyticsData}
      />
    </div>
  );
}
