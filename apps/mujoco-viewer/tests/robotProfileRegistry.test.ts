import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { ViewerRobotProfileRegistry } from "../src/robot-profiles/registry.js";
import { decodeViewerRobotDeclaration, viewerRobotProfileFromPayload } from "../src/robot-profiles/declaration.js";
import type { ViewerRobotProfile } from "../src/robot-profiles/types.js";
import {
  FAST_ARM_VIEWER_DECLARATION_DOCUMENT,
  FAST_ARM_VIEWER_PROFILE,
} from "./testViewerProfile.js";

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

  it("rejects malformed declarations and metadata mismatches before rendering", () => {
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
      () => viewerRobotProfileFromPayload({
        version: 0,
        frame_index: 0,
        time_s: 0,
        qpos: [0, 0, 0, 0],
        qvel: [0, 0, 0, 0],
        bodies: [],
        sites: [],
        target_position_m: null,
        metadata: {
          robot_profile_id: "other",
          model_contract_version: FAST_ARM_VIEWER_PROFILE.modelContractVersion,
          robot_joint_names: Array.from(FAST_ARM_VIEWER_PROFILE.jointNames),
          robot_qpos_dimension: FAST_ARM_VIEWER_PROFILE.qposDimension,
          viewer_robot_declaration: {
            schemaVersion: "viewer-robot-declaration/v1",
          },
        },
      }),
      /keys mismatch/,
    );
  });

  it("resolves a valid startup declaration from authoritative payload metadata", () => {
    const resolved = viewerRobotProfileFromPayload({
      version: 0,
      frame_index: 0,
      time_s: 0,
      qpos: [0, 0, 0, 0],
      qvel: [0, 0, 0, 0],
      bodies: [],
      sites: [],
      target_position_m: null,
      metadata: {
        robot_profile_id: FAST_ARM_VIEWER_PROFILE.profileId,
        model_contract_version: FAST_ARM_VIEWER_PROFILE.modelContractVersion,
        robot_joint_names: Array.from(FAST_ARM_VIEWER_PROFILE.jointNames),
        robot_qpos_dimension: FAST_ARM_VIEWER_PROFILE.qposDimension,
        viewer_robot_declaration: FAST_ARM_VIEWER_DECLARATION_DOCUMENT,
      },
    });

    assert.equal(resolved.profileId, FAST_ARM_VIEWER_PROFILE.profileId);
    assert.equal(resolved.modelUrl, FAST_ARM_VIEWER_PROFILE.modelUrl);
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

  it("validates the test-only second robot without a viewer source registration", () => {
    const declaration = decodeViewerRobotDeclaration(
      JSON.parse(
        readFileSync(
          resolve(
            process.cwd(),
            "..",
            "..",
            "tests",
            "fixtures",
            "robot_plugins",
            "assets",
            "mujoco",
            "fixture_bot",
            "viewer-profile.json",
          ),
          "utf8",
        ),
      ) as unknown,
    );

    assert.equal(declaration.profileId, "fixture_bot");
    assert.deepEqual(declaration.jointNames, ["fixture_joint"]);
    assert.equal(declaration.qposDimension, 1);
  });
});
