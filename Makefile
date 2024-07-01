OBJECTS = anchor celsius degiro kucoinx financas caixabreak luna20 cryptocom aforronet metamask
OBJECTSGCC = snailtrail
OBJECTSCHROMIUM = plutus ibfetch
OBJECTSALL = $(OBJECTS) $(OBJECTSGCC) $(OBJECTSCHROMIUM)
BASE_IMAGE_NAME = ghcr.io/fopina/balances
PLATFORMS = linux/amd64,linux/arm64
TARGETBASE = alpine
ACTION = load
PYTHON_VERSION = 3.9
DOCKER_EXTRA =
SUFFIX = 

.PHONY: list base base-gcc base-chromium base-alpine templ-base templ templ-gcc templ-chromium $(OBJECTSALL) $(addprefix push/,$(OBJECTSALL))

list:
	@echo $(OBJECTSALL)

base: base-alpine base-gcc base-chromium

base-gcc:
	make templ-base TARGETBASE=gcc

base-chromium:
	make templ-base TARGETBASE=chromium

base-alpine:
	make templ-base TARGETBASE=alpine

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
		make templ TARGETBASE=gcc

templ-chromium:
		make templ TARGETBASE=chromium

# FIXME: SERVICE=$@ does not work as variable declaration...
$(OBJECTS):
	SERVICE=$@ make templ PLATFORMS=$(shell docker system info --format '{{.OSType}}/{{.Architecture}}')

$(OBJECTSGCC):
	SERVICE=$@ make templ-gcc PLATFORMS=$(shell docker system info --format '{{.OSType}}/{{.Architecture}}')

$(OBJECTSCHROMIUM):
	SERVICE=$@ make templ-chromium PLATFORMS=$(shell docker system info --format '{{.OSType}}/{{.Architecture}}')

$(addprefix push/,$(OBJECTSALL)):
	make $(notdir $@) ACTION=push

all: $(OBJECTSALL)
