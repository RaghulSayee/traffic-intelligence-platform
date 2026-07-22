export type AnalyticsMetric = {
  key: string;
  label: string;
  value: number;
};

export type AnalyticsTrendPoint = {
  date: string;
  label: string;
  violations: number;
  confirmed: number;
  rejected: number;
};

export type CameraAnalytics = {
  cameraId: string;
  cameraName: string;
  location: string | null;
  total: number;
  pending: number;
  confirmed: number;
  rejected: number;
};

export type AnalyticsSummary = {
  totalViolations: number;
  pendingViolations: number;
  confirmedViolations: number;
  rejectedViolations: number;
  averageConfidence: number | null;
  totalJobs: number;
  successfulJobs: number;
  failedJobs: number;
  processingSuccessRate: number | null;
};

export type AnalyticsDashboardData = {
  summary: AnalyticsSummary;
  violationsByType: AnalyticsMetric[];
  violationsByReviewStatus: AnalyticsMetric[];
  jobsByStatus: AnalyticsMetric[];
  violationTrend: AnalyticsTrendPoint[];
  cameras: CameraAnalytics[];
};
