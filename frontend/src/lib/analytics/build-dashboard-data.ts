import type {
  AnalyticsDashboardData,
  AnalyticsMetric,
  AnalyticsTrendPoint,
  CameraAnalytics,
} from "@/types/analytics";
import type {
  ProcessingJob,
} from "@/types/api";
import type {
  ViolationEvent,
} from "@/types/violations";

type CameraRecord = {
  id: string;
  name: string;
  location: string | null;
};

const violationTypeLabels: Record<
  string,
  string
> = {
  no_helmet: "No Helmet",
  triple_riding: "Triple Riding",
  red_light: "Red Light",
  wrong_way: "Wrong Way",
  lane_violation: "Lane Violation",
  illegal_parking: "Illegal Parking",
  speeding: "Speeding",
  mobile_phone: "Mobile Phone",
  seatbelt: "Seatbelt",
};

const reviewStatusLabels: Record<
  string,
  string
> = {
  pending: "Pending",
  confirmed: "Confirmed",
  rejected: "Rejected",
};

const jobStatusLabels: Record<
  string,
  string
> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  cancelled: "Cancelled",
};

function formatUnknownLabel(
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

function createMetricCollection(
  counts: Map<string, number>,
  labels: Record<string, string>,
): AnalyticsMetric[] {
  return Array.from(
    counts.entries(),
  )
    .map(([key, value]) => ({
      key,
      label:
        labels[key] ??
        formatUnknownLabel(key),
      value,
    }))
    .sort(
      (first, second) =>
        second.value - first.value,
    );
}

function getViolationConfidence(
  violation: ViolationEvent,
): number | null {
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
    return null;
  }

  return (
    values.reduce(
      (sum, value) => sum + value,
      0,
    ) / values.length
  );
}

function toUtcDateKey(
  date: Date,
): string {
  return [
    date.getUTCFullYear(),
    String(
      date.getUTCMonth() + 1,
    ).padStart(2, "0"),
    String(
      date.getUTCDate(),
    ).padStart(2, "0"),
  ].join("-");
}

function createViolationTrend(
  violations: ViolationEvent[],
  numberOfDays = 14,
): AnalyticsTrendPoint[] {
  const counts = new Map<
    string,
    {
      violations: number;
      confirmed: number;
      rejected: number;
    }
  >();

  for (const violation of violations) {
    const occurredAt =
      new Date(
        violation.occurred_at,
      );

    if (
      Number.isNaN(
        occurredAt.getTime(),
      )
    ) {
      continue;
    }

    const dateKey =
      toUtcDateKey(occurredAt);

    const current =
      counts.get(dateKey) ?? {
        violations: 0,
        confirmed: 0,
        rejected: 0,
      };

    current.violations += 1;

    if (
      violation.review_status ===
      "confirmed"
    ) {
      current.confirmed += 1;
    }

    if (
      violation.review_status ===
      "rejected"
    ) {
      current.rejected += 1;
    }

    counts.set(
      dateKey,
      current,
    );
  }

  const result:
    AnalyticsTrendPoint[] = [];

  const today = new Date();

  for (
    let dayOffset =
      numberOfDays - 1;
    dayOffset >= 0;
    dayOffset -= 1
  ) {
    const date = new Date(
      Date.UTC(
        today.getUTCFullYear(),
        today.getUTCMonth(),
        today.getUTCDate() -
          dayOffset,
      ),
    );

    const dateKey =
      toUtcDateKey(date);

    const values =
      counts.get(dateKey) ?? {
        violations: 0,
        confirmed: 0,
        rejected: 0,
      };

    result.push({
      date: dateKey,
      label:
        new Intl.DateTimeFormat(
          "en-US",
          {
            month: "short",
            day: "numeric",
            timeZone: "UTC",
          },
        ).format(date),
      violations:
        values.violations,
      confirmed:
        values.confirmed,
      rejected:
        values.rejected,
    });
  }

  return result;
}

function createCameraAnalytics(
  violations: ViolationEvent[],
  cameras: CameraRecord[],
): CameraAnalytics[] {
  const camerasById = new Map(
    cameras.map((camera) => [
      camera.id,
      camera,
    ]),
  );

  const counts = new Map<
    string,
    CameraAnalytics
  >();

  for (const violation of violations) {
    const cameraId =
      violation.camera_id ??
      "unassigned";

    const camera =
      violation.camera_id
        ? camerasById.get(
            violation.camera_id,
          )
        : undefined;

    const current =
      counts.get(cameraId) ?? {
        cameraId,
        cameraName:
          camera?.name ??
          "Unassigned camera",
        location:
          camera?.location ??
          null,
        total: 0,
        pending: 0,
        confirmed: 0,
        rejected: 0,
      };

    current.total += 1;

    if (
      violation.review_status ===
      "pending"
    ) {
      current.pending += 1;
    }

    if (
      violation.review_status ===
      "confirmed"
    ) {
      current.confirmed += 1;
    }

    if (
      violation.review_status ===
      "rejected"
    ) {
      current.rejected += 1;
    }

    counts.set(
      cameraId,
      current,
    );
  }

  return Array.from(
    counts.values(),
  ).sort(
    (first, second) =>
      second.total - first.total,
  );
}

export function buildAnalyticsDashboardData({
  violations,
  jobs,
  cameras,
  violationTotal,
  jobTotal,
}: {
  violations: ViolationEvent[];
  jobs: ProcessingJob[];
  cameras: CameraRecord[];
  violationTotal?: number;
  jobTotal?: number;
}): AnalyticsDashboardData {
  const violationTypeCounts =
    new Map<string, number>();

  const reviewStatusCounts =
    new Map<string, number>();

  const jobStatusCounts =
    new Map<string, number>();

  const confidenceValues:
    number[] = [];

  for (const violation of violations) {
    violationTypeCounts.set(
      violation.violation_type,
      (
        violationTypeCounts.get(
          violation.violation_type,
        ) ?? 0
      ) + 1,
    );

    reviewStatusCounts.set(
      violation.review_status,
      (
        reviewStatusCounts.get(
          violation.review_status,
        ) ?? 0
      ) + 1,
    );

    const confidence =
      getViolationConfidence(
        violation,
      );

    if (confidence !== null) {
      confidenceValues.push(
        confidence,
      );
    }
  }

  for (const job of jobs) {
    jobStatusCounts.set(
      job.status,
      (
        jobStatusCounts.get(
          job.status,
        ) ?? 0
      ) + 1,
    );
  }

  const pendingViolations =
    reviewStatusCounts.get(
      "pending",
    ) ?? 0;

  const confirmedViolations =
    reviewStatusCounts.get(
      "confirmed",
    ) ?? 0;

  const rejectedViolations =
    reviewStatusCounts.get(
      "rejected",
    ) ?? 0;

  const successfulJobs =
    jobStatusCounts.get(
      "succeeded",
    ) ?? 0;

  const failedJobs =
    jobStatusCounts.get(
      "failed",
    ) ?? 0;

  const completedJobs =
    successfulJobs +
    failedJobs;

  const averageConfidence =
    confidenceValues.length
      ? confidenceValues.reduce(
          (sum, value) =>
            sum + value,
          0,
        ) /
        confidenceValues.length
      : null;

  const processingSuccessRate =
    completedJobs > 0
      ? successfulJobs /
        completedJobs
      : null;

  return {
    summary: {
      totalViolations:
        violationTotal ??
        violations.length,
      pendingViolations,
      confirmedViolations,
      rejectedViolations,
      averageConfidence,
      totalJobs:
        jobTotal ??
        jobs.length,
      successfulJobs,
      failedJobs,
      processingSuccessRate,
    },

    violationsByType:
      createMetricCollection(
        violationTypeCounts,
        violationTypeLabels,
      ),

    violationsByReviewStatus:
      createMetricCollection(
        reviewStatusCounts,
        reviewStatusLabels,
      ),

    jobsByStatus:
      createMetricCollection(
        jobStatusCounts,
        jobStatusLabels,
      ),

    violationTrend:
      createViolationTrend(
        violations,
      ),

    cameras:
      createCameraAnalytics(
        violations,
        cameras,
      ),
  };
}
