make clean
python3 -m build
python3 -m twine upload --verbose --repository testpypi dist/*
