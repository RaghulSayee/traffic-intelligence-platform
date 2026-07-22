export function formatFileSize(
  bytes: number,
): string {
  if (bytes === 0) {
    return "0 bytes";
  }

  const units = [
    "bytes",
    "KB",
    "MB",
    "GB",
  ];

  const unitIndex = Math.min(
    Math.floor(
      Math.log(bytes) / Math.log(1024),
    ),
    units.length - 1,
  );

  const value =
    bytes / 1024 ** unitIndex;

  return `${value.toFixed(
    unitIndex === 0 ? 0 : 1,
  )} ${units[unitIndex]}`;
}

export function formatDuration(
  seconds: number | null,
): string {
  if (seconds === null) {
    return "Unknown";
  }

  const totalSeconds = Math.round(
    seconds,
  );

  const minutes = Math.floor(
    totalSeconds / 60,
  );

  const remainingSeconds =
    totalSeconds % 60;

  return `${minutes}:${remainingSeconds
    .toString()
    .padStart(2, "0")}`;
}
