ARG PYTHON_VER
ARG IMAGE_TAG
ARG BASE_IMAGE=python:${PYTHON_VER}-${IMAGE_TAG}

FROM ${BASE_IMAGE} AS builder

ENV PATH "/root/.local/bin:${PATH}"

ADD conf /opt/app_src/conf
ADD pypepper /opt/app_src/pypepper
ADD example/server /opt/app_src/example/server
ADD scripts /opt/app_src/scripts
COPY git.json /opt/app_src/
COPY requirements.txt /opt/app_src/

WORKDIR /opt/app_src

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    procps \
    iputils-ping
RUN python -m pip install --disable-pip-version-check --no-cache-dir --user -r requirements.txt
RUN python ./scripts/build.py

FROM ${BASE_IMAGE} AS runtime

ENV PATH "/root/.local/bin:${PATH}"
ENV PYTHONPATH "${PYTHONPATH}:/opt/app/"

COPY --from=builder /root/.local /root/.local
COPY --from=builder /opt/app_src/dist /opt/app
COPY --from=builder /opt/app_src/git.json /opt/app/

USER root
WORKDIR /opt/app
ENTRYPOINT [ "python" ]
CMD ["example/server/app.py", "--config", "./conf/app.config.yaml"]
