import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { resolve, sep } from "node:path";
import { describe, it } from "node:test";
import loadMujoco from "@mujoco/mujoco";
import {
  decodeViewerRobotDeclaration,
  loadViewerRobotProfileFromPayload,
  validateViewerRobotProfileCompatibility,
  validateViewerRobotProfileFrameReference,
  viewerRobotDeclarationReferenceFromPayload,
  viewerRobotProfileDigest,
} from "../src/robot-profiles/declaration.js";
import { ViewerRobotProfileRegistry } from "../src/robot-profiles/registry.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";
import type { ViewerRobotProfile } from "../src/robot-profiles/types.js";
import {
  FAST_ARM_VIEWER_DECLARATION_DOCUMENT,
  FAST_ARM_VIEWER_PROFILE,
} from "./testViewerProfile.js";

const FAST_ARM_DECLARATION_DIGEST =
  "sha256:0a35ec57fe704fc6bb853e53db9f449a0721c751ece19addf787dfa50cce58e6";
const FIXTURE_DECLARATION_DIGEST =
  "sha256:08438401168fc3351f7e6733bbdef3dda6f207018a2c77d52cbf865798723ded";

function payloadFor(
  profile: ViewerRobotProfile,
  metadata: Record<string, unknown> = {},
): TransportPayloadV0 {
  return {
    version: 0,
    frame_index: 0,
    time_s: 0,
    qpos: Array.from({ length: profile.qposDimension }, () => 0),
    qvel: [],
    bodies: [],
    sites: [],
    target_position_m: null,
    metadata: {
      robot_profile_id: profile.profileId,
      model_contract_version: profile.modelContractVersion,
      robot_joint_names: Array.from(profile.jointNames),
      robot_qpos_dimension: profile.qposDimension,
      ...metadata,
    },
  };
}

describe("viewer robot profile registry", () => {
  it("resolves an explicitly decoded profile", () => {
    const registry = new ViewerRobotProfileRegistry([FAST_ARM_VIEWER_PROFILE]);
    assert.equal(registry.resolve("fast_arm"), FAST_ARM_VIEWER_PROFILE);
    assert.equal("meshFallbackUrls" in FAST_ARM_VIEWER_PROFILE, false);
    assert.ok(FAST_ARM_VIEWER_PROFILE.vfsAssets.size > 0);
  });

  it("rejects unknown and duplicate registrations explicitly", () => {
    const registry = new ViewerRobotProfileRegistry([FAST_ARM_VIEWER_PROFILE]);
    assert.throws(() => registry.resolve("unknown"), /unknown viewer robot profile ID/);
    assert.throws(
      () => new ViewerRobotProfileRegistry([FAST_ARM_VIEWER_PROFILE, FAST_ARM_VIEWER_PROFILE]),
      /duplicate viewer robot profile registration/,
    );
  });

  it("rejects malformed, remote, escaped, and mismatched resource URLs", () => {
    assert.throws(
      () => decodeViewerRobotDeclaration({ ...FAST_ARM_VIEWER_PROFILE, schemaVersion: "unknown/v1" }),
      /keys mismatch|unsupported viewer robot declaration schema version/,
    );
    assert.throws(
      () => decodeViewerRobotDeclaration({
        ...FAST_ARM_VIEWER_DECLARATION_DOCUMENT,
        modelUrl: "https://example.invalid/model.xml",
      }),
      /local absolute-path URL/,
    );
    assert.throws(
      () => decodeViewerRobotDeclaration({
        ...FAST_ARM_VIEWER_DECLARATION_DOCUMENT,
        modelResourcePath: "../outside.xml",
      }),
      /repository-relative POSIX path/,
    );
    assert.throws(
      () => decodeViewerRobotDeclaration({
        ...FAST_ARM_VIEWER_DECLARATION_DOCUMENT,
        modelUrl: "/mujoco/other_robot/model.xml",
      }),
      /model resource path\/URL mismatch/,
    );
    assert.throws(
      () =>
        viewerRobotDeclarationReferenceFromPayload(
          payloadFor(FAST_ARM_VIEWER_PROFILE, {
            viewer_robot_declaration_resource_path:
              "assets/mujoco/fast_arm/viewer-profile.json",
            viewer_robot_declaration_url: "https://example.invalid/viewer-profile.json",
            viewer_robot_declaration_digest: FAST_ARM_DECLARATION_DIGEST,
          }),
        ),
      /local absolute-path URL/,
    );
    assert.throws(
      () =>
        viewerRobotDeclarationReferenceFromPayload(
          payloadFor(FAST_ARM_VIEWER_PROFILE, {
            viewer_robot_declaration_resource_path: "../viewer-profile.json",
            viewer_robot_declaration_url: "/viewer-profile.json",
            viewer_robot_declaration_digest: FAST_ARM_DECLARATION_DIGEST,
          }),
        ),
      /repository-relative POSIX path/,
    );
  });

  it("uses the same canonical digest as the Python declaration contract", async () => {
    assert.equal(await viewerRobotProfileDigest(FAST_ARM_VIEWER_PROFILE), FAST_ARM_DECLARATION_DIGEST);
  });

  it("loads once at session startup and validates compact frame references", async () => {
    let fetchCount = 0;
    const fetcher = (async () => {
      fetchCount += 1;
      return new Response(JSON.stringify(FAST_ARM_VIEWER_DECLARATION_DOCUMENT), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }) as typeof fetch;
    const startupPayload = payloadFor(FAST_ARM_VIEWER_PROFILE, {
      viewer_robot_declaration_resource_path: "assets/mujoco/fast_arm/viewer-profile.json",
      viewer_robot_declaration_url: "/mujoco/fast_arm/viewer-profile.json",
      viewer_robot_declaration_digest: FAST_ARM_DECLARATION_DIGEST,
    });
    const startup = await loadViewerRobotProfileFromPayload(startupPayload, fetcher);

    assert.equal(fetchCount, 1);
    assert.equal(startup.profile.profileId, "fast_arm");
    assert.doesNotThrow(() =>
      validateViewerRobotProfileFrameReference(
        { ...startupPayload, frame_index: 1 },
        startup.reference,
        startup.profile,
      ),
    );
    assert.equal(fetchCount, 1, "steady-state frames must not refetch or decode the declaration");
    assert.throws(
      () =>
        validateViewerRobotProfileFrameReference(
          payloadFor(startup.profile, {
            ...startupPayload.metadata,
            viewer_robot_declaration_digest: `sha256:${"1".repeat(64)}`,
          }),
          startup.reference,
          startup.profile,
        ),
      /changed during the session/,
    );
    assert.throws(
      () =>
        validateViewerRobotProfileFrameReference(
          payloadFor(startup.profile),
          startup.reference,
          startup.profile,
        ),
      /disappeared during the session/,
    );
  });

  it("preserves generic payload compatibility when no declaration reference is present", () => {
    const payload = payloadFor(FAST_ARM_VIEWER_PROFILE);
    assert.equal(viewerRobotDeclarationReferenceFromPayload(payload), null);
    assert.doesNotThrow(() =>
      validateViewerRobotProfileCompatibility(payload, FAST_ARM_VIEWER_PROFILE),
    );
  });

  it("fetches the test-only second robot declaration, model, VFS, and fixture over HTTP", async () => {
    const fixtureRoot = resolve(
      process.cwd(),
      "..",
      "..",
      "tests",
      "fixtures",
      "robot_plugins",
    );
    const assetRoot = resolve(fixtureRoot, "assets");
    const server = createServer((request, response) => {
      const requestPath = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
      const repositoryPath = resolve(assetRoot, `.${requestPath}`);
      if (!repositoryPath.startsWith(assetRoot + sep)) {
        response.writeHead(403).end();
        return;
      }
      try {
        const content = readFileSync(repositoryPath);
        response.writeHead(200, {
          "content-type": requestPath.endsWith(".json")
            ? "application/json"
            : "application/xml",
        });
        response.end(content);
      } catch {
        response.writeHead(404).end();
      }
    });
    await new Promise<void>((resolveListen, rejectListen) => {
      server.once("error", rejectListen);
      server.listen(0, "127.0.0.1", resolveListen);
    });
    try {
      const address = server.address();
      assert.ok(address !== null && typeof address !== "string");
      const origin = `http://127.0.0.1:${address.port}`;
      let declarationFetchCount = 0;
      const fetcher = ((input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), origin);
        if (url.pathname.endsWith("viewer-profile.json")) {
          declarationFetchCount += 1;
        }
        return fetch(url, init);
      }) as typeof fetch;
      const declarationDocument = JSON.parse(
        readFileSync(
          resolve(assetRoot, "mujoco", "fixture_bot", "viewer-profile.json"),
          "utf8",
        ),
      ) as unknown;
      const fixtureProfile = decodeViewerRobotDeclaration(declarationDocument);
      const startupPayload = payloadFor(fixtureProfile, {
        viewer_robot_declaration_resource_path:
          "assets/mujoco/fixture_bot/viewer-profile.json",
        viewer_robot_declaration_url: "/mujoco/fixture_bot/viewer-profile.json",
        viewer_robot_declaration_digest: FIXTURE_DECLARATION_DIGEST,
      });

      const firstConnection = await loadViewerRobotProfileFromPayload(startupPayload, fetcher);
      const reconnect = await loadViewerRobotProfileFromPayload(startupPayload, fetcher);
      assert.equal(declarationFetchCount, 2, "each connection must reacquire the declaration");
      assert.equal(firstConnection.profile.profileId, "fixture_bot");
      assert.equal(firstConnection.profile.profileContractVersion, 2);
      assert.equal(reconnect.reference.digest, firstConnection.reference.digest);

      const resourceUrls = [
        firstConnection.profile.modelUrl,
        firstConnection.profile.fixtureUrl,
        ...firstConnection.profile.vfsAssets.values(),
      ];
      for (const url of resourceUrls) {
        const response = await fetcher(url);
        assert.equal(response.ok, true, `expected browser resource fetch to succeed: ${url}`);
      }
      const modelResponse = await fetcher(firstConnection.profile.modelUrl);
      const modelXml = await modelResponse.text();
      assert.match(modelXml, /<mujoco/);

      const mujoco = await loadMujoco({
        locateFile: () =>
          resolve(process.cwd(), "node_modules", "@mujoco", "mujoco", "mujoco.wasm"),
      });
      const vfs = new mujoco.MjVFS();
      let model: { nq: number; nv: number; delete(): void } | null = null;
      try {
        for (const [vfsPath, url] of firstConnection.profile.vfsAssets) {
          const response = await fetcher(url);
          assert.equal(response.ok, true);
          vfs.addBuffer(vfsPath, new Uint8Array(await response.arrayBuffer()));
        }
        const loadedModel = mujoco.MjModel.from_xml_string(modelXml, vfs);
        model = loadedModel;
        assert.equal(loadedModel.nq, 1);
        assert.equal(loadedModel.nv, 1);
      } finally {
        model?.delete();
        vfs.delete();
      }
    } finally {
      await new Promise<void>((resolveClose, rejectClose) =>
        server.close((error) => (error === undefined ? resolveClose() : rejectClose(error))),
      );
    }
  });

  it("does not equate generic joint count with qpos dimension", () => {
    const ballJointProfile: ViewerRobotProfile = {
      ...FAST_ARM_VIEWER_PROFILE,
      profileId: "ball_joint_test",
      jointNames: ["ball_joint"],
      qposDimension: 4,
    };
    const registry = new ViewerRobotProfileRegistry([ballJointProfile]);
    assert.equal(registry.resolve("ball_joint_test"), ballJointProfile);
  });
});
