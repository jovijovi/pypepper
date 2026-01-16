import shutil

# Copy code
shutil.copytree("./conf", "./dist/conf")
shutil.copytree("./pypepper", "./dist/pypepper")
shutil.copytree("./example", "./dist/example")
shutil.copytree("./.venv", "./dist/.venv")
