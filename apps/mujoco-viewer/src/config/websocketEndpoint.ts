export type ViewerEndpointConfigSource = "query" | "disabled";

export interface ViewerEndpointConfig {
  websocketUrl: string | null;
  source: ViewerEndpointConfigSource;
}

function readQueryParam(search: string, names: string[]): string | null {
  const searchParams = new URLSearchParams(search);
  for (const name of names) {
    const value = searchParams.get(name);
    if (value !== null) {
      return value;
    }
  }

  return null;
}

function normalizeWebSocketUrl(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "ws:" && parsed.protocol !== "wss:") {
      return null;
    }

    return trimmed;
  } catch {
    return null;
  }
}

export function readViewerEndpointConfig(
  locationLike: Pick<Location, "search">,
): ViewerEndpointConfig {
  const queryValue = readQueryParam(locationLike.search, ["websocketUrl", "ws"]);
  if (queryValue === null) {
    return {
      websocketUrl: null,
      source: "disabled",
    };
  }

  const websocketUrl = normalizeWebSocketUrl(queryValue);
  if (websocketUrl === null) {
    return {
      websocketUrl: null,
      source: "disabled",
    };
  }

  return {
    websocketUrl,
    source: "query",
  };
}
