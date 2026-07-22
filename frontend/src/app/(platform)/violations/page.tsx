import {
  AlertCircle,
} from "lucide-react";

import {
  ViolationsBrowser,
} from "@/components/violations/violations-browser";
import {
  PageHeader,
} from "@/components/ui/page-header";
import {
  getCameras,
  getVideos,
} from "@/lib/api/resources";
import {
  getViolations,
} from "@/lib/api/violations";
import type {
  ViolationListResponse,
} from "@/types/violations";

export const dynamic = "force-dynamic";

const emptyResponse: ViolationListResponse = {
  items: [],
  total: 0,
  offset: 0,
  limit: 100,
};

export default async function ViolationsPage() {
  let violations = emptyResponse;
  let cameras: Array<{
    id: string;
    name: string;
    location: string | null;
  }> = [];

  let videos: Array<{
    id: string;
    original_filename: string;
  }> = [];

  let loadError = false;

  try {
    const [
      violationResponse,
      cameraResponse,
      videoResponse,
    ] = await Promise.all([
      getViolations({
        limit: 100,
      }),
      getCameras({
        limit: 100,
      }),
      getVideos({
        limit: 100,
      }),
    ]);

    violations =
      violationResponse;

    cameras =
      cameraResponse.items.map(
        (camera) => ({
          id: camera.id,
          name: camera.name,
          location:
            camera.location,
        }),
      );

    videos =
      videoResponse.items.map(
        (video) => ({
          id: video.id,
          original_filename:
            video.original_filename,
        }),
      );
  } catch {
    loadError = true;
  }

  return (
    <>
      <PageHeader
        eyebrow="Violation review"
        title="Detected traffic violations"
        description="Inspect detected events, supporting evidence, confidence information, and review state."
      />

      {loadError ? (
        <div className="mb-6 flex gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle
            size={19}
            className="shrink-0"
          />

          Some violation information could not
          be loaded. Confirm that the backend
          is running.
        </div>
      ) : null}

      <ViolationsBrowser
        initialResponse={violations}
        cameras={cameras}
        videos={videos}
      />
    </>
  );
}
