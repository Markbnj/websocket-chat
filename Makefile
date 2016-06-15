CHAT_IMAGE_NAME ?= chat-connect
CHAT_CONTAINER_NAME := $(CHAT_IMAGE_NAME)
CONTENT_IMAGE_NAME ?= chat-content
CONTENT_CONTAINER_NAME := $(CONTENT_IMAGE_NAME)
IMAGE_TAG ?= 0.0.1

.chat-image:
	(docker ps -a | awk '$$NF == "$(CHAT_CONTAINER_NAME)" {exit 1}') || docker rm -f $(CHAT_CONTAINER_NAME)
	(docker images | awk '$$1 == "$(CHAT_IMAGE_NAME)" {exit 1}') || docker rmi $(CHAT_IMAGE_NAME)
	rm -f docker_build_chat.log
	cp Dockerfile.chat Dockerfile
	docker build --tag=$(CHAT_IMAGE_NAME) --rm=true --force-rm=true . | tee docker_build_chat.log
	rm -f Dockerfile

.content-image:
	(docker ps -a | awk '$$NF == "$(CONTENT_CONTAINER_NAME)" {exit 1}') || docker rm -f $(CONTENT_CONTAINER_NAME)
	(docker images | awk '$$1 == "$(CONTENT_IMAGE_NAME)" {exit 1}') || docker rmi $(CONTENT_IMAGE_NAME)
	rm -f docker_build_content.log
	cp Dockerfile.content Dockerfile
	docker build --tag=$(CONTENT_IMAGE_NAME) --rm=true --force-rm=true . | tee docker_build_content.log
	rm -f Dockerfile

run: .chat-image .content-image
	docker run -d --name=$(CHAT_CONTAINER_NAME) --expose=8080 -p 8080:8080 $(CHAT_IMAGE_NAME)
	docker run -d --name=$(CONTENT_CONTAINER_NAME) --expose=8088 -p 8088:8088 $(CONTENT_IMAGE_NAME)
	sleep 1
	xdg-open 'http://localhost:8088/'
	xdg-open 'http://localhost:8088/operator/'

run-chat: .chat-image
	docker run -d --name=$(CHAT_CONTAINER_NAME) --expose=8080 -p 8080:8080 $(CHAT_IMAGE_NAME)

run-chat-shell: .chat-image
	docker run -it --name=$(CHAT_CONTAINER_NAME) --expose=8080 -p 8080:8080 --entrypoint=bash $(CHAT_IMAGE_NAME)

run-content: .content-image
	docker run -d --name=$(CONTENT_CONTAINER_NAME) --expose=8088 -p 8088:8088 $(CONTENT_IMAGE_NAME)

run-content-shell: .content-image
	docker run -it --name=$(CONTENT_CONTAINER_NAME) --expose=8088 -p 8088:8088 --entrypoint=bash $(CONTENT_IMAGE_NAME)

build: .chat-image .content-image
