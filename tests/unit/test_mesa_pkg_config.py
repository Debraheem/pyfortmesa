from __future__ import annotations

import importlib.util
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = REPO_ROOT / "tools" / "mesa_pkg_config.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("mesa_pkg_config", HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_pc(directory: Path, name: str = "mesa-eos.pc") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("Name: mesa-eos\nVersion: test\n")
    return path


@contextmanager
def mesa_dir_env(path: Path):
    old = os.environ.get("MESA_DIR")
    os.environ["MESA_DIR"] = str(path)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("MESA_DIR", None)
        else:
            os.environ["MESA_DIR"] = old


def test_pkg_config_path_finds_installed_and_build_layouts():
    helper = load_helper()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        installed = root / "lib" / "pkgconfig"
        build = root / "build" / "dev" / "lib" / "pkgconfig"
        write_pc(installed, "mesa-const.pc")
        write_pc(build, "mesa-eos.pc")

        with mesa_dir_env(root):
            got = helper.pkg_config_path().split(os.pathsep)

        assert [Path(item).resolve() for item in got] == [
            installed.resolve(),
            build.resolve(),
        ]


def test_pkg_config_path_finds_direct_build_layout():
    helper = load_helper()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        direct_build = root / "build" / "lib" / "pkgconfig"
        write_pc(direct_build, "mesa-kap.pc")

        with mesa_dir_env(root):
            got = helper.pkg_config_path().split(os.pathsep)

        assert [Path(item).resolve() for item in got] == [direct_build.resolve()]


def test_pkg_config_path_error_mentions_shared_mesa():
    helper = load_helper()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with mesa_dir_env(root):
            try:
                helper.pkg_config_path()
            except SystemExit as exc:
                message = str(exc)
            else:
                raise AssertionError("pkg_config_path should fail without mesa-*.pc files")

    assert "No MESA pkg-config files" in message
    assert "USE_SHARED = YES" in message
    assert "lib/pkgconfig" in message
    assert "build/*/lib/pkgconfig" in message


def test_split_link_args_separates_rpaths():
    helper = load_helper()
    link_args, rpaths = helper.split_link_args(
        "-L/a -lfoo -Wl,-rpath,/a -Wl,-rpath,/a -Wl,-rpath /b -L/c"
    )

    assert link_args == ["-L/a", "-lfoo", "-L/c"]
    assert rpaths == ["/a", "/b"]


if __name__ == "__main__":
    test_pkg_config_path_finds_installed_and_build_layouts()
    test_pkg_config_path_finds_direct_build_layout()
    test_pkg_config_path_error_mentions_shared_mesa()
    test_split_link_args_separates_rpaths()
