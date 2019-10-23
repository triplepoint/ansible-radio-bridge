FROM python:3.8
LABEL maintainer="Jonathan Hanson <jonathan@jonathan-hanson.org>"

WORKDIR /usr/src/app

RUN pip install --no-cache-dir --upgrade \
    pip \
    pipenv \
    setuptools \
    wheel

COPY Pipfile ./
COPY Pipfile.lock ./

RUN pipenv install --deploy

COPY serial_bridge.py ./

CMD ["pipenv", "run", "python3", "./serial_bridge.py"]
