import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import {
  buildViewerRuntimeSnapshot,
  createViewerRuntime,
  type ViewerDocumentLike,
  type ViewerElementLike,
} from "../src/viewerRuntime.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

class FakeElement implements ViewerElementLike {
  public id = "";
  public className = "";
  public textContent: string | null = "";
  public readonly attributes = new Map<string, string>();
  public readonly children: FakeElement[] = [];
  public parent: FakeElement | null = null;

  constructor(
    public readonly tagName: string,
    private readonly ownerDocument: FakeDocument,
  ) {}

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
    if (name === "id") {
      this.id = value;
      this.ownerDocument.register(this);
    }
  }

  appendChild(child: FakeElement): void {
    child.parent = this;
    this.children.push(child);
    if (child.id !== "") {
      this.ownerDocument.register(child);
    }
  }

  replaceChildren(...children: Array<FakeElement | string>): void {
    this.children.splice(0, this.children.length);
    for (const child of children) {
      if (typeof child === "string") {
        continue;
      }

      this.appendChild(child);
    }
  }

  remove(): void {
    if (this.parent === null) {
      return;
    }

    this.parent.children.splice(this.parent.children.indexOf(this), 1);
    this.parent = null;
  }
}

class FakeDocument implements ViewerDocumentLike {
  public readonly body: FakeElement;
  private readonly elementsById = new Map<string, FakeElement>();

  constructor() {
    this.body = new FakeElement("body", this);
  }

  createElement(tagName: string): FakeElement {
    return new FakeElement(tagName, this);
  }

  getElementById(id: string): FakeElement | null {
    return this.elementsById.get(id) ?? null;
  }

  register(element: FakeElement): void {
    if (element.id === "") {
      return;
    }

    this.elementsById.set(element.id, element);
  }
}

function createAppShell(): { document: FakeDocument; app: FakeElement } {
  const document = new FakeDocument();
  const app = document.createElement("div");
  app.setAttribute("id", "app");
  document.body.appendChild(app);
  return { document, app };
}

function testBuildViewerRuntimeSnapshot(): void {
  const snapshot = buildViewerRuntimeSnapshot(payloadV0Fixture);

  assert(snapshot.payloadVersion === 0, "snapshot should keep payload version 0");
  assert(snapshot.frameIndex === 1, "snapshot should reflect the fixture frame");
  assert(snapshot.statusText.includes("payload v0"), "snapshot should advertise payload v0");
  assert(snapshot.summaryText.includes("base_link"), "snapshot should include base_link");
  assert(snapshot.summaryText.includes("tip"), "snapshot should include tip");
  assert(snapshot.markerScene.bodies.length === 1, "fixture should produce one body marker");
  assert(snapshot.markerScene.sites.length === 1, "fixture should produce one site marker");
}

function testCreateViewerRuntimeMountsAndStops(): void {
  const { document, app } = createAppShell();
  const runtime = createViewerRuntime({ document, payload: payloadV0Fixture });

  runtime.start();

  assert(app.children.length === 1, "viewer runtime should mount a single root");

  const root = app.children[0];
  assert(root.className === "viewer-runtime", "viewer runtime root class should be set");
  assert(
    root.attributes.get("data-runtime") === "mujoco-viewer",
    "viewer runtime root should identify the app",
  );
  assert(
    root.attributes.get("data-runtime-phase") === "browser-entry",
    "viewer runtime root should record the browser entry phase",
  );

  const statusSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-status");
  const sceneSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-scene");

  assert(statusSection !== undefined, "viewer runtime should render a status section");
  assert(sceneSection !== undefined, "viewer runtime should render a scene placeholder");
  assert(
    sceneSection?.textContent?.includes("Marker rendering placeholder") ?? false,
    "viewer runtime should advertise the placeholder scene",
  );

  runtime.stop();

  assert(app.children.length < 1, "viewer runtime stop should remove the mounted root");
  assert(document.getElementById("app") === app, "mount point should remain available after stop");
}

testBuildViewerRuntimeSnapshot();
testCreateViewerRuntimeMountsAndStops();

console.log("viewer runtime tests passed");
