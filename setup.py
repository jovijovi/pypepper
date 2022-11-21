import shutil

# Remote dist dir
shutil.rmtree("./dist")

# Copy code
shutil.copytree("./conf", "./dist/conf")
shutil.copytree("./pypedro", "./dist/pypedro")
shutil.copytree("./example", "./dist/example")
