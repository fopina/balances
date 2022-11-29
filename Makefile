OBJECTS = anchor celsius degiro kucoinx financas caixabreak luna20 cryptocom
OBJECTSGCC = snailtrail
OBJECTSCHROMIUM = plutus ibfetch
BASE_IMAGE_NAME = ghcr.io/fopina/balances
PLATFORMS = linux/amd64,linux/arm/v7,linux/arm64
ACTION = push
DOCKER_EXTRA =

templ:
		docker buildx build \
	              --platform $(PLATFORMS) \
				  -t $(BASE_IMAGE_NAME):$(SERVICE)-$(shell git log --oneline $(SERVICE).py | wc -l | tr -d ' ') \
				  -t $(BASE_IMAGE_NAME):$(SERVICE) \
				  --build-arg ENTRY=$(SERVICE) $(DOCKER_EXTRA) \
				  -f docker/Dockerfile \
				  --$(ACTION) .

templ-gcc:
		docker buildx build \
	              --platform $(PLATFORMS) \
				  -t $(BASE_IMAGE_NAME):$(SERVICE)-$(shell git log --oneline $(SERVICE).py | wc -l | tr -d ' ') \
				  -t $(BASE_IMAGE_NAME):$(SERVICE) \
				  --build-arg ENTRY=$(SERVICE) --build-arg TARGETBASE=gcc $(DOCKER_EXTRA) \
				  -f docker/Dockerfile \
				  --$(ACTION) .

templ-chromium:
		docker buildx build \
	              --platform $(PLATFORMS) \
				  -t $(BASE_IMAGE_NAME):$(SERVICE)-$(shell git log --oneline $(SERVICE).py | wc -l | tr -d ' ') \
				  -t $(BASE_IMAGE_NAME):$(SERVICE) \
				  --build-arg ENTRY=$(SERVICE) --build-arg TARGETBASE=chromium $(DOCKER_EXTRA) \
				  -f docker/Dockerfile \
				  --$(ACTION) .

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
