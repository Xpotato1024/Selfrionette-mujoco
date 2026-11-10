"""既知のエンジン不具合に該当する実効モデルを実行前に拒否する。"""
from __future__ import annotations


def validate_solver_compatibility(model: object) -> None:
    """4.0.0の疎行列Newtonを拒否し、数値条件は暗黙に変更しない。"""
    import mujoco

    if (
        mujoco.mj_versionString() == "4.0.0"
        and model.opt.solver == mujoco.mjtSolver.mjSOL_NEWTON
        and mujoco.mj_isSparse(model)
    ):
        raise ValueError(
            "MuJoCo 4.0.0 sparse Newton is unsupported due to upstream issue #3767; "
            "use a separately validated engine/model configuration. "
            "No automatic solver or Jacobian fallback is applied."
        )
