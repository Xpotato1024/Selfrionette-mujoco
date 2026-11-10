"""自己pilotの条件準備・試行対応・保存値の再解析を行うCLI。"""
from pathlib import Path
import json


def add_experiment_parser(commands):
    parser = commands.add_parser("experiment", help="自己pilotの4条件・試行順・結果解析（実機操作なし）")
    actions = parser.add_subparsers(dest="experiment_action", required=True)
    prepare = actions.add_parser("prepare", help="S/Gの明示条件から同一速度係数の4条件と試行順を保存")
    prepare.add_argument("--gamepad-condition", type=Path, required=True)
    prepare.add_argument("--selfrionette-condition", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True, help="新規の出力directory")
    prepare.add_argument("--participant-id", required=True, help="氏名を含まない匿名ID")
    prepare.add_argument("--session-id", required=True)
    prepare.add_argument("--repetitions", type=int, required=True, help="4条件を実施する反復数。研究上の推奨値は設定しない")
    prepare.add_argument("--order-row", type=int, choices=range(4), required=True, help="釣合い順序の開始行0..3。反復ごとに次行へ進む")
    prepare.add_argument("--speed-m-s", type=float, required=True, help="明示する共通の単軸速度係数")
    prepare.add_argument("--software-revision", required=True)
    prepare.add_argument("--protocol-note", required=True, help="課題・目標・基準提示/待機/練習/休止規則の所在と未確定事項")
    prepare.add_argument("--software-fixture", action="store_true", help="合成入力の検証専用session。実操作者結果とは区別")
    attach = actions.add_parser("attach", help="完了trialを条件・revision照合後にslotへ対応付ける")
    attach.add_argument("--session", type=Path, required=True)
    attach.add_argument("--slot", type=int, required=True)
    attach.add_argument("--trial-directory", type=Path, required=True)
    attach.add_argument("--attempt", type=int, default=1)
    attach.add_argument("--retry-reason")
    attach.add_argument("--response", type=Path, help="感覚報告・推定回答・phase区間等の明示JSON。元trialは変更しない")
    analyze = actions.add_parser("analyze", help="保存の整合性を検査し全試行のJSON/CSV/ばね時系列図を再生成")
    analyze.add_argument("--result-root", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--session", type=Path)
    analyze.add_argument("--spring-object", help="誤差の対象となるばねobject ID")
    analyze.add_argument("--target-force-n", type=float, help="ばね復元荷重kqの目標N。接触力や入力力ではない")
    analyze.add_argument("--window-start-s", type=float)
    analyze.add_argument("--window-end-s", type=float)
    analyze.add_argument("--no-plots", action="store_true")


def run_experiment(args):
    if args.experiment_action == "prepare":
        from xpotato_sim.runtime.experiment.pilot_session import create_session, read_condition
        result = create_session(gamepad=read_condition(args.gamepad_condition),
            selfrionette=read_condition(args.selfrionette_condition), output=args.output,
            participant_id=args.participant_id, session_id=args.session_id,
            repetitions=args.repetitions, order_row=args.order_row, speed_m_s=args.speed_m_s,
            software_revision=args.software_revision, software_fixture=args.software_fixture,
            protocol_note=args.protocol_note)
        print(json.dumps({"session_file": str(args.output.resolve() / "session.json"),
            "trial_slots": len(result["trials"]), "usage": result["usage"],
            "readiness": result["readiness"]}, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    if args.experiment_action == "attach":
        from xpotato_sim.runtime.experiment.pilot_session import attach_trial
        from xpotato_sim.runtime.scene.objects import strict_json
        response = None
        if args.response is not None:
            with args.response.open("rb") as stream:
                response = strict_json(stream.read(8193), max_bytes=8192)
        result = attach_trial(session_path=args.session, slot=args.slot, trial_directory=args.trial_directory,
            attempt=args.attempt, retry_reason=args.retry_reason, response=response)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    from xpotato_sim.runtime.experiment.pilot_export import export_results
    report = export_results(result_root=args.result_root, output=args.output, session_path=args.session,
        spring_object=args.spring_object, target_force_n=args.target_force_n,
        window_start_s=args.window_start_s, window_end_s=args.window_end_s, plots=not args.no_plots)
    print(json.dumps({"analysis_file": str(args.output.resolve() / "analysis.json"),
        **{key: report[key] for key in ("trial_count", "verified_count", "invalid_or_incomplete_count", "stop_reasons", "participant_count", "software_fixture_id_count", "missing_linked_trial_ids", "unlinked_trial_ids", "unattempted_slots", "session_linkage_complete")}},
        ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if report["invalid_or_incomplete_count"] or report["session_linkage_complete"] is False else 0
