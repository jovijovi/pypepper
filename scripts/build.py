import os
import shutil

# Copy code into dist for runtime packaging (Docker / make build).
# .venv is optional locally; Docker build creates it before this script runs.
for src, dst in (
    ("./conf", "./dist/conf"),
    ("./pypepper", "./dist/pypepper"),
    ("./example", "./dist/example"),
):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

venv_src = "./.venv"
venv_dst = "./dist/.venv"
if os.path.isdir(venv_src):
    if os.path.exists(venv_dst):
        shutil.rmtree(venv_dst)
    shutil.copytree(venv_src, venv_dst)
else:
    print("[BUILD] .venv not found; skipped (use `python -m build` for PyPI packages)")
