APP_NAME:=pypepper
OS:=linux
PYTHON_VER:=3.13.14
IMAGE_TAG:=slim-trixie

PROJECT_DIR:=$(shell pwd -L)
GIT_BRANCH:=$(shell git -C "${PROJECT_DIR}" rev-parse --abbrev-ref HEAD | grep -v HEAD || git describe --tags || git -C "${PROJECT_DIR}" rev-parse --short HEAD)
GIT_COMMIT:=$(shell git rev-parse --short HEAD)
GIT_DIR:=$(shell pwd -L|xargs basename)
BUILD_DIR:=$(PROJECT_DIR)/dist
APP_DIR:=$(BUILD_DIR)
PYTHON_PATH=$(PROJECT_DIR)
DOCKER_DIR:=$(PROJECT_DIR)/docker
DOCKER_FILE=./docker/Dockerfile

VERSION=$(GIT_BRANCH).$(GIT_COMMIT)
COMMIT_TIME=$(shell git show -s --format=%cd $(GIT_COMMIT) --date=format:"%Y%m%d%H%M")
BUILD_TIME=$(shell date -u '+%Y%m%d%H%M')
APP_TAG=$(VERSION).$(BUILD_TIME)
VERSION_INFO='{"version":"$(VERSION)","gitCommit":"$(GIT_COMMIT)","commitTime":"$(COMMIT_TIME)","buildTime":"$(BUILD_TIME)","pythonVersion":"$(PYTHON_VER)"}'


.PHONY: build-prepare debug test build docker clean publish-test publish help check lint docs docs-serve audit

all: test clean docker

build-prepare: clean
	@echo "[BUILD] Prepare for building..."
	mkdir -p $(APP_DIR)
	uv pip install -r requirements-dev.txt

lint:
	@echo "[BUILD] Running ruff and mypy..."
	ruff check pypepper
	ruff format --check pypepper
	mypy pypepper

docs:
	@echo "[BUILD] Building documentation..."
	mkdocs build --strict

docs-serve:
	@echo "[BUILD] Serving documentation..."
	mkdocs serve

audit:
	@echo "[BUILD] Auditing production requirements..."
	python3 -m pip install -q pip-audit
	python3 ./scripts/pip_audit.py

check: lint
	@echo "[BUILD] Checking mutable class attributes..."
	python3 ./scripts/check_mutable_class_attrs.py

test: clean check
	@echo "[BUILD] Testing"
	pytest --cov=pypepper --cov-report=xml:coverage.xml --cov-report=term --cov-fail-under=90 tests/

build: build-prepare
	@echo "[BUILD] Building binary"
	uv pip install -r requirements.txt
	python ./scripts/build.py
	@echo $(VERSION_INFO) > $(APP_DIR)/git.json

docker:
	@echo "[BUILD] Building docker image..."
	@echo $(VERSION_INFO) > $(PROJECT_DIR)/git.json
	docker buildx build \
	  --pull \
	  --load \
	  --force-rm \
	  -f $(DOCKER_FILE) \
	  --build-arg PYTHON_VER=$(PYTHON_VER) \
	  --build-arg IMAGE_TAG=$(IMAGE_TAG) \
	  -t $(APP_NAME):$(APP_TAG) .
	docker tag $(APP_NAME):$(APP_TAG) $(APP_NAME):latest
	docker images|grep $(APP_NAME)
	@echo "[BUILD] The Docker image has been built."

clean:
	@echo "[BUILD] Cleaning..."
	rm -rf ./dist/
	rm -rf .pytest_cache
	rm -rf .coverage
	@echo "[BUILD] Cleaned"

publish-test: clean
	python3 -m build
	python3 -m twine upload --verbose --repository testpypi dist/*

publish: clean
	python3 -m build
	python3 -m twine upload --repository pypi dist/*

help:
	@cat ./docs/makefile/help.txt
