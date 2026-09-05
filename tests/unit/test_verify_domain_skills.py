import importlib.util
import sys
from pathlib import Path


def test_explicit_checkout_runtime_does_not_require_repointing_global_link(tmp_path, monkeypatch, capsys):
    path = Path(__file__).parents[2] / "scripts/verify_domain_skills.py"
    spec = importlib.util.spec_from_file_location("verify_domain_skills", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DEFAULT_LINK", tmp_path / "missing-global-link")
    monkeypatch.setattr(sys, "argv", [str(path), "--runtime-workspace", str(module.ROOT.parent)])
    assert module.main() == 0
    assert "PASS" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", [str(path), "--runtime-workspace", str(tmp_path)])
    assert module.main() == 1
    monkeypatch.setattr(sys, "argv", [str(path)])
    assert module.main() == 1
