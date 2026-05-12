lint:
	ruff check --fix
	ruff format

lint-check:
	ruff check
	ruff format --check

selenium:
	docker run --rm -d \
           --name selenium_balances \
           --shm-size 2g \
           -e SE_START_XVFB='true' \
           -e SE_START_VNC='true' \
           -e SE_INV=a \
           -e SE_VNC_NO_PASSWORD='1' \
           -p 7900:7900 \
           selenium/standalone-chromium:147.0
