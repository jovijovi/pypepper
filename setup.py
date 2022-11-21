import shutil

shutil.copytree("./conf", "./dist/conf")
shutil.copytree("./pypedro", "./dist/pypedro")
shutil.copytree("./example", "./dist/example")
shutil.copyfile("./git.json", "./dist/git.json")
