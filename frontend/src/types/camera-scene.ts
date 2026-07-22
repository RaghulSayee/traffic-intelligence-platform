export type SceneViolationType =
  | "no_helmet"
  | "triple_riding"
  | "red_light"
  | "wrong_way"
  | "lane_violation"
  | "speeding";

export type NormalizedPoint = {
  x: number;
  y: number;
};

export type NormalizedDirection = {
  x: number;
  y: number;
};

export type NormalizedPolygon = {
  points: NormalizedPoint[];
};

export type NormalizedLine = {
  start: NormalizedPoint;
  end: NormalizedPoint;
};

export type LaneConfiguration = {
  lane_id: string;
  name: string | null;
  polygon: NormalizedPolygon;
  allowed_direction: NormalizedDirection;
  speed_limit_kph: number | null;
};

export type TrafficLightRegionConfiguration = {
  region_id: string;
  name: string | null;
  polygon: NormalizedPolygon;
};

export type StopLineConfiguration = {
  stop_line_id: string;
  lane_id: string | null;
  traffic_light_region_id: string | null;
  line: NormalizedLine;
};

export type SpeedCalibrationSegment = {
  segment_id: string;
  line: NormalizedLine;
  distance_meters: number;
};

export type CameraSceneConfiguration = {
  schema_version: "1.0";
  enabled_violations: SceneViolationType[];
  monitoring_zone: NormalizedPolygon | null;
  lanes: LaneConfiguration[];
  traffic_light_regions:
    TrafficLightRegionConfiguration[];
  stop_lines: StopLineConfiguration[];
  speed_calibration_segments:
    SpeedCalibrationSegment[];
  metadata: Record<string, unknown>;
};

export const emptyCameraScene:
  CameraSceneConfiguration = {
  schema_version: "1.0",
  enabled_violations: [],
  monitoring_zone: null,
  lanes: [],
  traffic_light_regions: [],
  stop_lines: [],
  speed_calibration_segments: [],
  metadata: {},
};
