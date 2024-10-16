APP_NAME:=pypepper
OS:=linux
PYTHON_VER:=3.10.15
IMAGE_TAG:=slim-bookworm

PROJECT_DIR:=$(shell pwd -L)
GIT_BRANCH:=$(shell git -C "${PROJECT_DIR}" rev-parse --abbrev-ref HEAD | grep -v HEAD || git describe --tags || git -C "${PROJECT_DIR}" rev-parse --short HEAD)
GIT_COMMIT:=$(if $(CI_COMMIT_SHORT_SHA),$(CI_COMMIT_SHORT_SHA),$(shell git rev-parse --short HEAD))
GIT_DIR:=$(shell pwd -L|xargs basename)
BUILD_DIR:=$(PROJECT_DIR)/dist
APP_DIR:=$(BUILD_DIR)
DOCKER_DIR:=$(PROJECT_DIR)/docker
PYTHON_PATH=$(PROJECT_DIR)

TIMESTAMP:=$(shell date -u '+%Y%m%d')
VER1:=$(if $(CI_COMMIT_TAG),$(CI_COMMIT_TAG).$(GIT_COMMIT),$(if $(CI_COMMIT_SHORT_SHA),$(CI_COMMIT_SHORT_SHA),$(GIT_BRANCH).$(GIT_COMMIT)))
VER:=$(if $(CI_Daily_Build),$(VER1).$(TIMESTAMP),$(VER1))

Version=$(VER)
GitCommit=$(GIT_COMMIT)
BuildTime=$(TIMESTAMP)
VERSION_INFO='{"version":"$(Version)","gitCommit":"$(GitCommit)","buildTime":"$(BuildTime)","pythonVersion":"$(PYTHON_VER)"}'

ifneq ($(unsafe_docker),)
DOCKER_FILE=./docker/Dockerfile.debug
else
DOCKER_FILE=./docker/Dockerfile
endif

.PHONY: build-prepare debug test build docker clean publish-test publish help

all: test clean docker

build-prepare: clean
	@echo "[MAKEFILE] Prepare for building..."
	mkdir -p $(APP_DIR)
	python -m pip install -r requirements-dev.txt

debug: build-prepare
	@echo "[MAKEFILE] Building debug"

test: clean
	@echo "[MAKEFILE] Testing"
	pytest --cov=pypepper tests/

build: build-prepare
	@echo "[MAKEFILE] Building binary"
	python -m pip install -r requirements.txt
	python ./scripts/build.py
	@echo $(VERSION_INFO) > $(APP_DIR)/git.json

docker:
	@echo "[MAKEFILE] Building docker image..."
	@echo $(VERSION_INFO) > $(PROJECT_DIR)/git.json
	docker build --force-rm -f $(DOCKER_FILE) --build-arg PYTHON_VER=$(PYTHON_VER) --build-arg IMAGE_TAG=$(IMAGE_TAG) -t $(APP_NAME):$(VER) .
	docker tag $(APP_NAME):$(VER) $(APP_NAME):latest
	docker images|grep $(APP_NAME)
	@echo "[MAKEFILE] Build docker image done"

clean:
	@echo "[MAKEFILE] Cleaning..."
	rm -rf ./dist/
	rm -rf .pytest_cache
	rm -rf .coverage
	@echo "[MAKEFILE] Cleaned"

publish-test: clean
	python3 -m build
	python3 -m twine upload --verbose --repository testpypi dist/*

publish: clean
	python3 -m build
	python3 -m twine upload --repository pypi dist/*

help:
	@echo "# Build code:\n  make build"
	@echo "# Build docker image:\n  make docker"
	@echo "# Clean:\n  make clean"
	@echo "# Test:\n  make test"
	@echo "# All:\n  make all"
	@echo "# Publish to testpypi:\n  make publish-test"
	@echo "# Publish to pypi:\n  make publish"
