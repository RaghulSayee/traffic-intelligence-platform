import {
  AlertCircle,
  Upload,
} from "lucide-react";
import Link from "next/link";

import {
  PageHeader,
} from "@/components/ui/page-header";
import {
  VideoLibrary,
} from "@/components/videos/video-library";
import {
  getCameras,
  getProcessingJobs,
  getVideos,
} from "@/lib/api/resources";
import type {
  ProcessingJob,
  Video,
} from "@/types/api";

export const dynamic = "force-dynamic";

type CameraRecord = {
  id: string;
  name: string;
  location: string | null;
};

export default async function VideosPage() {
  let videos: Video[] = [];
  let jobs: ProcessingJob[] = [];
  let cameras: CameraRecord[] = [];
  let loadError = false;

  try {
    const [
      videoResponse,
      jobResponse,
      cameraResponse,
    ] = await Promise.all([
      getVideos({
        limit: 100,
      }),
      getProcessingJobs({
        limit: 100,
      }),
      getCameras({
        limit: 100,
      }),
    ]);

    videos =
      videoResponse.items;

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
        eyebrow="Video library"
        title="Uploaded traffic videos"
        description="Browse uploaded footage, monitor processing status, inspect metadata, and open analysis jobs."
        action={
          <Link
            href="/videos/upload"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
          >
            <Upload size={18} />
            Upload video
          </Link>
        }
      />

      {loadError ? (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle
            size={19}
            className="mt-0.5 shrink-0"
          />

          Video information could not be loaded.
          Confirm that FastAPI and PostgreSQL
          are running.
        </div>
      ) : null}

      <VideoLibrary
        videos={videos}
        jobs={jobs}
        cameras={cameras}
      />
    </>
  );
}
