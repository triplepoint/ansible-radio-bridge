FROM python:3.10-alpine
LABEL maintainer="Jonathan Hanson <jonathan@jonathan-hanson.org>"

ARG UID_GID=1066

RUN addgroup -g $UID_GID app \
    && adduser -u $UID_GID -S -D -G app -s /usr/sbin/nologin app \
    && adduser app dialout

WORKDIR /usr/src/app

RUN pip install --no-cache-dir --upgrade \
    'pip' \
    'pipenv' \
    'setuptools' \
    'wheel'

COPY Pipfile ./
COPY Pipfile.lock ./

USER app

RUN pipenv install --deploy

COPY serial_bridge.py ./

CMD ["pipenv", "run", "python3", "./serial_bridge.py"]
