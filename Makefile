APP_NAME:=pedro.py
HUB:=$(if $(HUB),$(HUB),some_docker_image_repo)
OS:=linux
PYTHON_VER=$(shell python -V)
ALPINE_VER:=3.16

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

.PHONY: build-prepare debug test build docker help clean

all: docker

build-prepare:
	@echo "[MAKEFILE] Prepare for building..."
	mkdir -p $(APP_DIR)

debug: build-prepare
	@echo "[MAKEFILE] Building debug"

test: test
	@echo "[MAKEFILE] Testing"
	pytest --cache-clear

build: build-prepare
	@echo "[MAKEFILE] Building binary"
	@echo $(VERSION_INFO) > $(APP_DIR)/git.json

# TODO:
docker:
	@echo "[MAKEFILE] Building docker image..."
	@echo $(VERSION_INFO) > $(PROJECT_DIR)/git.json
	docker build --force-rm -f $(DOCKER_FILE) --build-arg PYTHON_VER=$(PYTHON_VER) -t $(APP_NAME):$(VER) .
	docker tag $(APP_NAME):$(VER) $(APP_NAME):latest
	docker images|grep $(APP_NAME)
	@echo "[MAKEFILE] Build docker image done"

clean:
	rm ./dist/ -rf
	@echo "[MAKEFILE] Cleaned"

help:
	@echo "make build -- Compile code"
	@echo "make docker -- Build docker image"