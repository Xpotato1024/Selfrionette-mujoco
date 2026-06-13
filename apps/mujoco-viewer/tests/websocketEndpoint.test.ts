import { readViewerEndpointConfig } from "../src/config/websocketEndpoint.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function testReadViewerEndpointConfigReadsWebsocketUrl(): void {
  const config = readViewerEndpointConfig({
    search: "?websocketUrl=ws://127.0.0.1:8766",
  });

  assert(config.websocketUrl === "ws://127.0.0.1:8766", "websocketUrl should be read from query");
  assert(config.source === "query", "source should be query when websocketUrl is present");
}

function testReadViewerEndpointConfigReadsWsAlias(): void {
  const config = readViewerEndpointConfig({
    search: "?ws=ws://127.0.0.1:8766",
  });

  assert(config.websocketUrl === "ws://127.0.0.1:8766", "ws alias should be supported");
  assert(config.source === "query", "source should be query when ws alias is present");
}

function testReadViewerEndpointConfigDisablesWhenMissingQuery(): void {
  const config = readViewerEndpointConfig({
    search: "",
  });

  assert(config.websocketUrl === null, "missing query should disable connection");
  assert(config.source === "disabled", "missing query should report disabled");
}

function testReadViewerEndpointConfigDisablesMalformedUrl(): void {
  const config = readViewerEndpointConfig({
    search: "?websocketUrl=not-a-websocket-url",
  });

  assert(config.websocketUrl === null, "malformed URL should be treated as disabled");
  assert(config.source === "disabled", "malformed URL should be reported as disabled");
}

testReadViewerEndpointConfigReadsWebsocketUrl();
testReadViewerEndpointConfigReadsWsAlias();
testReadViewerEndpointConfigDisablesWhenMissingQuery();
testReadViewerEndpointConfigDisablesMalformedUrl();

console.log("websocket endpoint tests passed");
