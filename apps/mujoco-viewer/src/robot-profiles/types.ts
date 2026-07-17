export interface ViewerBodyVisualStyle {
  color: string;
  label: string;
  detail: string;
}

export interface ViewerAxisVisualStyle {
  color: string;
  label: string;
  detail: string;
}

export interface ViewerRobotProfile {
  readonly schemaVersion: "viewer-robot-declaration/v1";
  readonly profileId: string;
  readonly profileContractVersion: number;
  readonly modelContractVersion: string;
  readonly modelUrl: string;
  readonly modelResourcePath: string;
  readonly initialKeyframeName: string;
  readonly initialPoseSourceLabel: string;
  readonly fixtureUrl: string;
  readonly vfsAssets: ReadonlyMap<string, string>;
  readonly vfsResourcePaths: ReadonlyMap<string, string>;
  readonly visualStyleSelection: ReadonlyMap<string, string>;
  readonly bodyVisualStyles: Readonly<Record<string, ViewerBodyVisualStyle>>;
  readonly axisVisualStyles: readonly ViewerAxisVisualStyle[];
  readonly jointNames: readonly string[];
  readonly qposDimension: number;
}
