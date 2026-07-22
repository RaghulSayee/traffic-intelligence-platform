import { PageHeader } from "@/components/ui/page-header";
import { VideoUploadForm } from "@/components/videos/video-upload-form";
import { getCameras } from "@/lib/api/resources";
import type { Camera } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function UploadVideoPage() {
  let cameras: Camera[] = [];
  let camerasAvailable = true;

  try {
    const response = await getCameras({
      limit: 100,
    });

    cameras = response.items;
  } catch {
    camerasAvailable = false;
  }

  return (
    <>
      <PageHeader
        eyebrow="New analysis"
        title="Upload traffic video"
        description="Submit recorded traffic footage, assign a camera scene, and configure processing priority."
      />

      <VideoUploadForm
        cameras={cameras}
        camerasAvailable={
          camerasAvailable
        }
      />
    </>
  );
}
