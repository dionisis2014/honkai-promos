FROM python:alpine

WORKDIR /usr/src/app

COPY main.py requirements.txt ./
RUN --mount=type=cache,target=/root/.cache \
    pip install -r requirements.txt

VOLUME /mnt
ENV HASS_HOST="homeassistant.lan" \
    HASS_USER="user" \
    HASS_PASS="password" \
    LOG_LEVEL="INFO" \
    RETRY_DELAY=10

ENTRYPOINT [ "python", "./main.py" ]
