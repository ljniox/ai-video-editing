from pathlib import Path

from autoedit.core.ingest import init_run_dir


def test_init_run_dir_tmp(tmp_path: Path):
    created = init_run_dir(tmp_path / "runs" / "t1")
    for key in ["raw", "audio", "proxies", "outputs", "artifacts", "logs"]:
        assert key in created
        assert Path(created[key]).exists()
