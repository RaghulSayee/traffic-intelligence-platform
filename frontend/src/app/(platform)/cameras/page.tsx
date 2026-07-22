import {
  AlertCircle,
} from "lucide-react";

import {
  CameraManager,
} from "@/components/cameras/camera-manager";
import {
  PageHeader,
} from "@/components/ui/page-header";
import {
  getCameraList,
} from "@/lib/api/cameras";
import type {
  CameraListResponse,
} from "@/types/cameras";

export const dynamic = "force-dynamic";

const emptyResponse:
  CameraListResponse = {
  items: [],
  total: 0,
  offset: 0,
  limit: 100,
};

export default async function CamerasPage() {
  let response =
    emptyResponse;

  let loadError = false;

  try {
    response =
      await getCameraList({
        limit: 100,
      });
  } catch {
    loadError = true;
  }

  return (
    <>
      <PageHeader
        eyebrow="Camera management"
        title="Traffic monitoring cameras"
        description="Register monitoring cameras, manage connectivity and video settings, and configure road scenes."
      />

      {loadError ? (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle
            size={19}
            className="mt-0.5 shrink-0"
          />

          Camera information could not be
          loaded. Confirm that FastAPI and
          PostgreSQL are running.
        </div>
      ) : null}

      <CameraManager
        initialResponse={response}
      />
    </>
  );
}
