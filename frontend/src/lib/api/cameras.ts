import {
  apiFetch,
} from "@/lib/api/client";
import type {
  Camera,
  CameraCreatePayload,
  CameraListQuery,
  CameraListResponse,
  CameraUpdatePayload,
} from "@/types/cameras";


async function cameraRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const headers = new Headers(
    options?.headers,
  );

  if (
    options?.body
    && !headers.has(
      "Content-Type",
    )
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  return apiFetch<T>(
    path,
    {
      ...options,
      headers,
    },
  );
}


export async function getCameraList(
  query: CameraListQuery = {},
): Promise<CameraListResponse> {
  const parameters =
    new URLSearchParams();

  parameters.set(
    "offset",
    String(
      query.offset ?? 0,
    ),
  );

  parameters.set(
    "limit",
    String(
      query.limit ?? 100,
    ),
  );

  if (query.status) {
    parameters.set(
      "status",
      query.status,
    );
  }

  return cameraRequest<
    CameraListResponse
  >(
    `/cameras?${parameters.toString()}`,
  );
}


export async function getCamera(
  cameraId: string,
): Promise<Camera> {
  return cameraRequest<Camera>(
    `/cameras/${encodeURIComponent(
      cameraId,
    )}`,
  );
}


export async function createCamera(
  payload: CameraCreatePayload,
): Promise<Camera> {
  return cameraRequest<Camera>(
    "/cameras",
    {
      method: "POST",
      body: JSON.stringify(
        payload,
      ),
    },
  );
}


export async function updateCamera(
  cameraId: string,
  payload: CameraUpdatePayload,
): Promise<Camera> {
  return cameraRequest<Camera>(
    `/cameras/${encodeURIComponent(
      cameraId,
    )}`,
    {
      method: "PATCH",
      body: JSON.stringify(
        payload,
      ),
    },
  );
}


export async function deleteCamera(
  cameraId: string,
): Promise<void> {
  return cameraRequest<void>(
    `/cameras/${encodeURIComponent(
      cameraId,
    )}`,
    {
      method: "DELETE",
    },
  );
}


export async function getCameraScene(
  cameraId: string,
): Promise<
  import(
    "@/types/camera-scene"
  ).CameraSceneConfiguration
> {
  return cameraRequest<
    import(
      "@/types/camera-scene"
    ).CameraSceneConfiguration
  >(
    `/cameras/${encodeURIComponent(
      cameraId,
    )}/scene`,
  );
}


export async function updateCameraScene(
  cameraId: string,
  scene: import(
    "@/types/camera-scene"
  ).CameraSceneConfiguration,
): Promise<
  import(
    "@/types/camera-scene"
  ).CameraSceneConfiguration
> {
  return cameraRequest<
    import(
      "@/types/camera-scene"
    ).CameraSceneConfiguration
  >(
    `/cameras/${encodeURIComponent(
      cameraId,
    )}/scene`,
    {
      method: "PUT",
      body: JSON.stringify(
        scene,
      ),
    },
  );
}
