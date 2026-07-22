type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined;

export function createQueryPath(
  path: string,
  values: Record<string, QueryValue>,
): string {
  const parameters = new URLSearchParams();

  for (const [key, value] of Object.entries(
    values,
  )) {
    if (
      value === undefined ||
      value === null ||
      value === ""
    ) {
      continue;
    }

    parameters.set(
      key,
      String(value),
    );
  }

  const query = parameters.toString();

  return query
    ? `${path}?${query}`
    : path;
}
