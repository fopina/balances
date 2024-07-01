OBJECTS := anchor celsius degiro kucoinx financas caixabreak luna20 cryptocom aforronet metamask
OBJECTSGCC := snailtrail
OBJECTSCHROMIUM := plutus ibfetch
OBJECTSALL = $(OBJECTS) $(OBJECTSGCC) $(OBJECTSCHROMIUM)
BASE_IMAGE_NAME := ghcr.io/fopina/balances
PLATFORMS := linux/amd64,linux/arm64
TEST_PLATFORM = $(shell docker system info --format '{{.OSType}}/{{.Architecture}}')
TARGETBASE = alpine
ACTION = push
PYTHON_VERSION = 3.9
DOCKER_EXTRA =
SUFFIX = 

.PHONY: list base base-gcc base-chromium base-alpine templ-base templ templ-gcc templ-chromium $(OBJECTSALL) $(addprefix test/,$(OBJECTSALL))

list:
	@echo $(OBJECTSALL) $(addprefix lite/,$(OBJECTSCHROMIUM))

base: base-alpine base-gcc base-chromium

base-gcc:
	$(MAKE) templ-base TARGETBASE=gcc

base-chromium:
	$(MAKE) templ-base TARGETBASE=chromium

base-alpine:
	$(MAKE) templ-base TARGETBASE=alpine

templ-base:
	docker buildx build \
				  --pull \
				  --platform $(PLATFORMS) \
				  --build-arg BASE=python:$(PYTHON_VERSION)-alpine \
				  --build-arg BASESLIM=python:$(PYTHON_VERSION)-slim \
				  -t $(BASE_IMAGE_NAME):base-$(PYTHON_VERSION)-$(TARGETBASE)$(SUFFIX)-$(shell git log --oneline docker | wc -l | tr -d ' ') \
				  -t $(BASE_IMAGE_NAME):base-$(PYTHON_VERSION)-$(TARGETBASE)$(SUFFIX) \
				  $(DOCKER_EXTRA) \
				  -f docker/Dockerfile.base \
				  --target $(TARGETBASE) \
				  --$(ACTION) .

templ:
	docker buildx build \
				  --platform $(PLATFORMS) \
				  --pull \
				  -t $(BASE_IMAGE_NAME):$(SERVICE)$(SUFFIX)-$(shell git log --oneline $(SERVICE).py docker | wc -l | tr -d ' ') \
				  -t $(BASE_IMAGE_NAME):$(SERVICE)$(SUFFIX) \
				  --build-arg TARGETBASE=ghcr.io/fopina/balances:base-$(PYTHON_VERSION)-$(TARGETBASE) \
				  --build-arg ENTRY=$(SERVICE) \
				  $(DOCKER_EXTRA) \
				  -f docker/Dockerfile \
				  --$(ACTION) .

templ-gcc:
	$(MAKE) templ TARGETBASE=gcc

templ-chromium:
	$(MAKE) templ TARGETBASE=chromium

$(OBJECTS):
	$(MAKE) templ SERVICE=$@

$(OBJECTSGCC):
	$(MAKE) templ-gcc SERVICE=$@

$(OBJECTSCHROMIUM):
	$(MAKE) templ-chromium SERVICE=$@

$(addprefix lite/,$(OBJECTSCHROMIUM)):
	$(MAKE) templ SERVICE=$(notdir $@)

$(addprefix test/lite/,$(OBJECTSCHROMIUM)):
	$(MAKE) lite/$(notdir $@) ACTION=load PLATFORMS=$(TEST_PLATFORM)

$(addprefix test/,$(OBJECTSALL)):
	$(MAKE) $(notdir $@) ACTION=load PLATFORMS=$(TEST_PLATFORM)

all: $(OBJECTSALL)
