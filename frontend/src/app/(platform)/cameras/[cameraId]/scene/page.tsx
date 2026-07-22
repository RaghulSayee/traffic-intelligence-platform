import {
  AlertCircle,
  ArrowLeft,
  Camera as CameraIcon,
  MapPin,
} from "lucide-react";
import Link from "next/link";

import {
  SceneEditor,
} from "@/components/cameras/scene-editor";
import {
  getCamera,
  getCameraScene,
} from "@/lib/api/cameras";
import type {
  Camera,
} from "@/types/cameras";
import type {
  CameraSceneConfiguration,
} from "@/types/camera-scene";

export const dynamic = "force-dynamic";

type CameraScenePageProps = {
  params: Promise<{
    cameraId: string;
  }>;
};

export default async function CameraScenePage({
  params,
}: CameraScenePageProps) {
  const { cameraId } =
    await params;

  let camera:
    | Camera
    | null = null;

  let scene:
    | CameraSceneConfiguration
    | null = null;

  let errorMessage:
    | string
    | null = null;

  try {
    [camera, scene] =
      await Promise.all([
        getCamera(cameraId),
        getCameraScene(cameraId),
      ]);
  } catch (error) {
    errorMessage =
      error instanceof Error
        ? error.message
        : "Camera scene could not be loaded.";
  }

  if (!camera || !scene) {
    return (
      <>
        <Link
          href="/cameras"
          className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
        >
          <ArrowLeft size={17} />
          Back to cameras
        </Link>

        <section className="mt-6 rounded-2xl border border-rose-200 bg-white p-10 text-center shadow-sm">
          <AlertCircle
            size={38}
            className="mx-auto text-rose-500"
          />

          <h1 className="mt-4 text-xl font-bold text-slate-950">
            Scene unavailable
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            {errorMessage}
          </p>
        </section>
      </>
    );
  }

  return (
    <>
      <Link
        href="/cameras"
        className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-700"
      >
        <ArrowLeft size={17} />
        Back to cameras
      </Link>

      <header className="mt-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Camera scene configuration
          </p>

          <h1 className="mt-2 flex items-center gap-3 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            <CameraIcon
              size={28}
              className="text-cyan-700"
            />

            {camera.name}
          </h1>

          <p className="mt-2 flex items-center gap-2 text-sm text-slate-500">
            <MapPin size={15} />
            {camera.location ??
              "No location configured"}
          </p>
        </div>

        <span className="w-fit rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold capitalize text-slate-700">
          {camera.status}
        </span>
      </header>

      <div className="mt-7">
        <SceneEditor
          camera={camera}
          initialScene={scene}
        />
      </div>
    </>
  );
}
