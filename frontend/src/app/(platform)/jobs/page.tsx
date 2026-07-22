import {
  JobsMonitor,
} from "@/components/jobs/jobs-monitor";
import {
  PageHeader,
} from "@/components/ui/page-header";
import {
  getCameras,
  getProcessingJobs,
  getVideos,
} from "@/lib/api/resources";
import type {
  Camera,
  ProcessingJob,
  Video,
} from "@/types/api";

export const dynamic =
  "force-dynamic";

export default async function JobsPage() {
  let jobs: ProcessingJob[] = [];
  let videos: Video[] = [];
  let cameras: Camera[] = [];

  let loadError:
    | string
    | null = null;

  try {
    const [
      jobsResponse,
      videosResponse,
      camerasResponse,
    ] = await Promise.all([
      getProcessingJobs({
        limit: 100,
      }),
      getVideos({
        limit: 100,
      }),
      getCameras({
        limit: 100,
      }),
    ]);

    jobs = jobsResponse.items;
    videos = videosResponse.items;
    cameras = camerasResponse.items;
  } catch (error) {
    loadError =
      error instanceof Error
        ? error.message
        : "Processing jobs could not be loaded.";
  }

  return (
    <>
      <PageHeader
        eyebrow="Processing"
        title="Analysis jobs"
        description="Monitor queued, running, completed, and failed video-analysis jobs."
      />

      {loadError ? (
        <section className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
          {loadError}
        </section>
      ) : null}

      <JobsMonitor
        jobs={jobs}
        videos={videos}
        cameras={cameras}
      />
    </>
  );
}
