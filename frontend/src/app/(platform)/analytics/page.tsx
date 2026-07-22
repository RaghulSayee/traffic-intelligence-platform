import {
  AlertCircle,
} from "lucide-react";

import {
  AnalyticsExplorer,
} from "@/components/analytics/analytics-explorer";
import {
  PageHeader,
} from "@/components/ui/page-header";
import {
  getCameras,
  getProcessingJobs,
} from "@/lib/api/resources";
import {
  getViolations,
} from "@/lib/api/violations";
import type {
  ProcessingJob,
} from "@/types/api";
import type {
  ViolationEvent,
} from "@/types/violations";

export const dynamic = "force-dynamic";

type CameraRecord = {
  id: string;
  name: string;
  location: string | null;
};

export default async function AnalyticsPage() {
  let violations:
    ViolationEvent[] = [];

  let jobs:
    ProcessingJob[] = [];

  let cameras:
    CameraRecord[] = [];

  let loadError = false;

  try {
    const [
      violationResponse,
      jobResponse,
      cameraResponse,
    ] = await Promise.all([
      getViolations({
        limit: 100,
      }),
      getProcessingJobs({
        limit: 100,
      }),
      getCameras({
        limit: 100,
      }),
    ]);

    violations =
      violationResponse.items;

    jobs =
      jobResponse.items;

    cameras =
      cameraResponse.items.map(
        (camera) => ({
          id: camera.id,
          name: camera.name,
          location:
            camera.location,
        }),
      );
  } catch {
    loadError = true;
  }

  return (
    <>
      <PageHeader
        eyebrow="Analytics"
        title="Traffic intelligence analytics"
        description="Explore violation trends, review outcomes, camera activity, confidence, and processing performance."
      />

      {loadError ? (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle
            size={19}
            className="mt-0.5 shrink-0"
          />

          Analytics information could not be
          loaded. Confirm that FastAPI and
          PostgreSQL are running.
        </div>
      ) : null}

      <AnalyticsExplorer
        violations={violations}
        jobs={jobs}
        cameras={cameras}
      />
    </>
  );
}
