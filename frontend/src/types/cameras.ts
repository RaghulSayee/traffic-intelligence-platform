export type CameraStatus =
  | "inactive"
  | "active"
  | "degraded"
  | "offline";

export type Camera = {
  id: string;
  name: string;
  location: string | null;
  description: string | null;
  stream_url: string | null;
  status: CameraStatus;
  latitude: number | null;
  longitude: number | null;
  configured_fps: number | null;
  resolution_width: number | null;
  resolution_height: number | null;
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CameraListResponse = {
  items: Camera[];
  total: number;
  offset: number;
  limit: number;
};

export type CameraCreatePayload = {
  name: string;
  location?: string | null;
  description?: string | null;
  stream_url?: string | null;
  status?: CameraStatus;
  latitude?: number | null;
  longitude?: number | null;
  configured_fps?: number | null;
  resolution_width?: number | null;
  resolution_height?: number | null;
  configuration?: Record<string, unknown>;
};

export type CameraUpdatePayload =
  Partial<CameraCreatePayload>;

export type CameraListQuery = {
  offset?: number;
  limit?: number;
  status?: CameraStatus;
};
