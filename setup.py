import shutil

shutil.copytree("./conf", "./dist/conf")
shutil.copytree("./pedro", "./dist/pedro")
shutil.copytree("./example", "./dist/example")
shutil.copyfile("./git.json", "./dist/git.json")
