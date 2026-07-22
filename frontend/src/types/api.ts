export type VideoStatus =
  | "uploaded"
  | "queued"
  | "processing"
  | "completed"
  | "failed";

export type ProcessingJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type ViolationType =
  | "no_helmet"
  | "triple_riding"
  | "red_light"
  | "wrong_way"
  | "lane_violation"
  | "illegal_parking"
  | "speeding"
  | "mobile_phone"
  | "seatbelt";

export type ReviewStatus =
  | "pending"
  | "confirmed"
  | "rejected";

export type JsonObject = Record<
  string,
  unknown
>;

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  offset: number;
  limit: number;
};

export type Video = {
  id: string;
  camera_id: string | null;
  original_filename: string;
  storage_key: string;
  content_type: string | null;
  source_type: string;
  status: VideoStatus;
  size_bytes: number | null;
  duration_seconds: number | null;
  frames_per_second: number | null;
  frame_count: number | null;
  width: number | null;
  height: number | null;
  checksum_sha256: string | null;
  video_metadata: JsonObject;
  created_at: string;
  updated_at: string;
};

export type ProcessingJob = {
  id: string;
  video_id: string;
  status: ProcessingJobStatus;
  progress_percent: number;
  priority: number;
  attempt_count: number;
  last_processed_frame: number;
  pipeline_name: string;
  pipeline_version: string | null;
  worker_id: string | null;
  claimed_at: string | null;
  heartbeat_at: string | null;
  lease_expires_at: string | null;
  model_versions: JsonObject;
  job_metrics: JsonObject;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ViolationEvent = {
  id: string;
  video_id: string;
  camera_id: string | null;
  processing_job_id: string;
  violation_type: ViolationType;
  review_status: ReviewStatus;
  occurred_at: string;
  frame_number: number | null;
  track_id: string | null;
  license_plate: string | null;
  detection_confidence: number | null;
  rule_confidence: number | null;
  ocr_confidence: number | null;
  evidence_image_key: string | null;
  evidence_clip_key: string | null;
  geometry: JsonObject;
  event_metadata: JsonObject;
  created_at: string;
  updated_at: string;
};

export type Camera = {
  id: string;
  name: string;
  location: string | null;
  description: string | null;
  stream_url: string | null;
  status: string;
  latitude: number | null;
  longitude: number | null;
  configured_fps: number | null;
  resolution_width: number | null;
  resolution_height: number | null;
  configuration: JsonObject;
  created_at: string;
  updated_at: string;
};

export type VideoUploadResponse = {
  video: Video;
  processing_job: ProcessingJob;
};
