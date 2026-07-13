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
  readonly profileId: string;
  readonly profileContractVersion: number;
  readonly modelContractVersion: string;
  readonly modelUrl: string;
  readonly initialKeyframeName: string;
  readonly initialPoseSourceLabel: string;
  readonly fixtureUrl: string;
  readonly vfsAssets: ReadonlyMap<string, string>;
  readonly meshFallbackUrls: ReadonlyMap<string, string>;
  readonly visualStyleSelection: ReadonlyMap<string, string>;
  readonly bodyVisualStyles: Readonly<Record<string, ViewerBodyVisualStyle>>;
  readonly axisVisualStyles: readonly ViewerAxisVisualStyle[];
  readonly jointNames: readonly string[];
  readonly qposDimension: number;
}
