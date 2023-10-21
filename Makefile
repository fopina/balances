OBJECTS = anchor celsius degiro kucoinx financas caixabreak luna20 cryptocom aforronet
OBJECTSGCC = snailtrail
OBJECTSCHROMIUM = plutus ibfetch
BASE_IMAGE_NAME = ghcr.io/fopina/balances
PLATFORMS = linux/amd64,linux/arm/v7,linux/arm64
TARGETBASE = alpine
ACTION = push
PYTHON_VERSION = 3.9
DOCKER_EXTRA =
SUFFIX = 

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
	SERVICE=$@ make templ PLATFORMS=linux/amd64 ACTION=load
$(addprefix push/,$(OBJECTS)):
	SERVICE=$(notdir $@) make templ ACTION=push

$(OBJECTSGCC):
	SERVICE=$@ make templ-gcc PLATFORMS=linux/amd64 ACTION=load
$(addprefix push/,$(OBJECTSGCC)):
	SERVICE=$(notdir $@) make templ-gcc ACTION=push

$(OBJECTSCHROMIUM):
	SERVICE=$@ make templ-chromium PLATFORMS=linux/amd64 ACTION=load
$(addprefix push/,$(OBJECTSCHROMIUM)):
	SERVICE=$(notdir $@) make templ-chromium ACTION=push

all: $(OBJECTS) $(OBJECTSGCC) $(OBJECTSCHROMIUM)
