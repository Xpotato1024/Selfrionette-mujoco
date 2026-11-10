"""有限試行内の連続記録。欠測はnullのまま保存し、表示用の丸め値を使わない。"""
from hashlib import sha256
import os
from xpotato_sim.runtime.scene.objects import canonical


class ContinuousRecord:
    """既存trial directoryに一つの有界JSONLを置く。demoはこのownerを作らない。"""
    def __init__(self, recorder, identity):
        self.recorder, self.identity = recorder, identity
        self.path = recorder.directory / "samples.jsonl.pending"
        self.size = 0
        self._failed = None
        self.digest = sha256()
        with self.path.open("xb"):
            pass

    def append(self, kind, **values):
        try:
            if self._failed is not None:
                raise OSError(self._failed)
            line = canonical({"schema_version": "trial-continuous/v1", **self.identity,
                "kind": kind, **values}) + b"\n"
            if self.size+len(line) > 64*1024*1024:
                raise OSError("continuous record 64 MiB bound exceeded")
            with self.path.open("ab") as stream:
                if stream.write(line) != len(line):
                    raise OSError("incomplete continuous write")
            self.size += len(line)
            self.digest.update(line)
        except Exception as exc:
            self._failed = str(exc)
            raise

    def finish(self):
        if self._failed is not None:
            raise OSError(self._failed)
        with self.path.open("rb+") as stream:
            stream.flush()
            os.fsync(stream.fileno())
            actual = sha256()
            while block := stream.read(65536):
                actual.update(block)
        if actual.digest() != self.digest.digest():
            raise OSError("continuous record read-back mismatch")
        target = self.path.with_name("samples.jsonl")
        os.link(self.path, target)
        self.path.unlink()
        return {"file": target.name, "sha256": actual.hexdigest(), "bytes": self.size}


def comparison_metrics(directory):
    """従来の戻り値を保ち、参照連鎖全体を検証した保存値から指標を返す。"""
    from .trial_analysis import analyze_trial
    result = analyze_trial(directory)
    return {**{key: result["metrics"][key] for key in
               ("ticks", "peak_spring_displacement_m", "peak_contact_force_n", "missing_measurements")},
            "runner_stop_reason": result["runner_stop_reason"], "task_outcome": result["task_outcome"]}
