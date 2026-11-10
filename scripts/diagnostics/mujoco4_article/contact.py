"""同じ MuJoCo 4 の投機的接触 OFF/ON を単一ステップで比較する。"""
import argparse
import json
from pathlib import Path
import mujoco
import numpy as np


def trial(enabled):
    flag = "enable" if enabled else "disable"
    xml = f'''<mujoco model="speculative single step">
<option timestep="0.02" gravity="0 0 0"><flag speculative="{flag}"/></option>
<worldbody><geom name="wall" type="box" size="0.005 0.2 0.2"/>
<body name="ball" pos="-0.12 0 0"><freejoint/><geom type="sphere" size="0.01" mass="0.1"/></body>
</worldbody></mujoco>'''
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    data.qvel[0] = 12
    records = []
    for index in range(13):
        mujoco.mj_forward(model, data)
        if not np.isfinite(data.qpos).all() or np.any(data.warning.number):
            raise RuntimeError("invalid state")
        records.append({"step": index, "time_s": float(data.time), "sphere_center_x_m": float(data.qpos[0]),
                        "velocity_x_m_s": float(data.qvel[0]), "contact_count": int(data.ncon)})
        if index != 12:
            mujoco.mj_step(model, data)
    return xml, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if mujoco.__version__ != "4.0.0":
        parser.error("requires isolated mujoco==4.0.0")
    args.output.mkdir(parents=True, exist_ok=False)
    results = {}
    for enabled in (False, True):
        name = "on" if enabled else "off"
        xml, rows = trial(enabled)
        (args.output / f"{name}.xml").write_text(xml, encoding="utf-8")
        results[name] = rows
    (args.output / "results.json").write_text(json.dumps({"mujoco": mujoco.__version__, "comparison": "4.0.0 flag OFF vs ON, not 3.x vs 4.x", "records": results}, indent=2) + "\n", encoding="utf-8")
    rows = []
    for i, name in enumerate(("off", "on")):
        y = 185 + i * 175
        x = 360 + results[name][1]["sphere_center_x_m"] * 1600
        text = f'{results[name][1]["sphere_center_x_m"] * 1000:.1f} mm'
        rows.append(f'''<text x="44" y="{y-60}" font-size="28">Speculative {name.upper()}</text>
<line x1="80" x2="660" y1="{y}" y2="{y}" stroke="#8093a5"/>
<rect x="352" y="{y-48}" width="16" height="96" fill="#99a5b2"/>
<circle cx="168" cy="{y}" r="16" fill="none" stroke="#8093a5" stroke-dasharray="5 4"/>
<line x1="188" x2="{x-20}" y1="{y}" y2="{y}" stroke="#2664a5" stroke-width="4" marker-end="url(#arrow)"/>
<circle cx="{x}" cy="{y}" r="16" fill="#2664a5"/>
<text x="168" y="{y+74}" text-anchor="middle" font-size="23">-120 mm</text>
<text x="{x}" y="{y-28}" text-anchor="middle" font-size="23">{text}</text>''')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 500" role="img" aria-labelledby="title desc">
<title id="title">Single-step tunneling test: speculative OFF / ON</title>
<desc id="desc">A sphere moves at 12 metres per second toward a ten millimetre thick wall. After twenty milliseconds its centre is at plus 120 millimetres with the flag off, and minus 17.1 millimetres with the flag on.</desc>
<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#2664a5"/></marker></defs>
<rect width="720" height="500" fill="#f5f7fa"/><g font-family="sans-serif" fill="#162b40">
<text x="44" y="48" font-size="30">Same model / after one 20 ms step</text>
<text x="44" y="88" font-size="23">12 m/s sphere / 10 mm wall / MuJoCo 4.0.0</text>
{''.join(rows)}<text x="360" y="473" text-anchor="middle" font-size="23">Wall centre: x = 0</text></g></svg>'''
    (args.output / "comparison.svg").write_text(svg, encoding="utf-8")
    print(json.dumps({key: rows[1] for key, rows in results.items()}))


if __name__ == "__main__":
    main()