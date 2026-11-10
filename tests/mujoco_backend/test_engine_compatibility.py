"""移行版・既知不具合の拒否・現行条件をnativeモデルで検証する。"""
from importlib.metadata import version
import mujoco
import pytest
from xpotato_sim.mujoco_backend.compatibility import validate_solver_compatibility
from xpotato_sim.mujoco_backend.model_loader import (
    load_mujoco_model, load_mujoco_model_from_xml_resources,
)
from xpotato_sim.runtime.composition.launch_profile import load_launch_profile


def model_xml(nv=1, jacobian="auto", solver="Newton"):
    bodies = "".join(
        f'<body pos="{i} 0 0"><joint/><geom size=".01" contype="0" conaffinity="0"/></body>'
        for i in range(nv)
    )
    return (f'<mujoco><option jacobian="{jacobian}" solver="{solver}"/>'
            f'<worldbody>{bodies}</worldbody></mujoco>').encode()


@pytest.mark.parametrize("jacobian,solver,nv,reject", [
    ("dense", "Newton", 1, False), ("sparse", "Newton", 1, True),
    ("auto", "Newton", 59, False), ("auto", "Newton", 60, True),
    ("auto", "Newton", 61, True),
    ("dense", "Newton", 61, False), ("sparse", "CG", 61, False),
    ("sparse", "PGS", 61, False),
])
def test_effective_solver_gate_without_changing_options(jacobian, solver, nv, reject):
    m = mujoco.MjModel.from_xml_string(model_xml(nv, jacobian, solver).decode())
    before = (int(m.opt.solver), int(m.opt.jacobian), int(m.opt.enableflags))
    if reject:
        with pytest.raises(ValueError, match="#3767"):
            validate_solver_compatibility(m)
    else:
        validate_solver_compatibility(m)
    assert before == (int(m.opt.solver), int(m.opt.jacobian), int(m.opt.enableflags))


@pytest.mark.parametrize("reported_version", ["3.9.0", "4.0.1"])
def test_gate_is_limited_to_known_affected_version(monkeypatch, reported_version):
    m = mujoco.MjModel.from_xml_string(model_xml(jacobian="sparse").decode())
    monkeypatch.setattr(mujoco, "mj_versionString", lambda: reported_version)
    validate_solver_compatibility(m)
    # 将来版の物理互換性を実測した意味ではない。版判定だけを検査する。


@pytest.mark.parametrize("resource", [False, True])
def test_loader_rejects_before_forward(tmp_path, monkeypatch, resource):
    xml = model_xml(jacobian="sparse")
    def forbidden(*args):
        raise AssertionError("forward must not run for the rejected solver")
    monkeypatch.setattr(mujoco, "mj_forward", forbidden)
    with pytest.raises(ValueError, match="#3767"):
        if resource:
            load_mujoco_model_from_xml_resources(xml, assets={}, logical_model_path="test.xml")
        else:
            path = tmp_path / "test.xml"
            path.write_bytes(xml)
            load_mujoco_model(path)


def test_provider_reset_rechecks_effective_solver_before_forward(monkeypatch):
    r = load_launch_profile("tasks/research-spring").build_model().provider
    r.model.opt.jacobian = mujoco.mjtJacobian.mjJAC_SPARSE
    def forbidden(*args):
        raise AssertionError("forward must not run for the rejected solver")
    monkeypatch.setattr(mujoco, "mj_forward", forbidden)
    with pytest.raises(ValueError, match="#3767"):
        r.reset()


@pytest.mark.parametrize("name,nv", [
    ("tasks/research-spring", 5), ("tasks/dynamic-fixed-contact", 8),
    ("tasks/dynamic-cube-drop", 14), ("tasks/dynamic-cube-push", 14),
])
def test_current_profiles_keep_dense_newton_and_speculative_disabled(name, nv):
    p = load_launch_profile(name)
    r = p.build_model().provider
    m = r.model
    assert version("mujoco") == mujoco.mj_versionString() == "4.0.0"
    assert m.nv == nv
    assert not mujoco.mj_isSparse(m)
    assert m.opt.solver == mujoco.mjtSolver.mjSOL_NEWTON
    assert m.opt.integrator == mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    assert m.opt.timestep == pytest.approx(1 / 600, abs=1e-15)
    assert not (m.opt.enableflags & mujoco.mjtEnableBit.mjENBL_SPECULATIVE)
    assert r.numerical_condition()["mujoco_version"] == "4.0.0"
    assert r.trial_state()["mujoco_version"] == "4.0.0"
