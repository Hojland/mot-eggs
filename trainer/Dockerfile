ARG IMAGE_NAME=nvidia/cuda:11.6.0-devel-ubuntu20.04
FROM $IMAGE_NAME

ARG PROD_ENV=production
ARG COMPUTE_KERNEL=gpu
ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHON_VERSION=3.10.4

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.2.0 \
    TOKENIZERS_PARALLELISM="false"

RUN if [ "$COMPUTE_KERNEL" = "gpu" ]; then \
    rm /etc/apt/sources.list.d/cuda.list \
    && apt-key del 7fa2af80 \
    && apt-get -y update && apt-get install -y --no-install-recommends wget \
    && wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb \
    && dpkg -i cuda-keyring_1.0-1_all.deb \
    ; else \
    echo "\n" \
    ; fi

RUN apt-get update -y && apt-get install -y \
    # General installations
    curl \
    gcc \
    g++

# for python installs
RUN apt install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    xz-utils \
    tk-dev \
    llvm \
    liblzma-dev \
    libreadline-dev \
    libffi-dev \
    libbz2-dev \
    python-openssl


# download and extract python sources
RUN cd /opt \
    && wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
    && tar xzf Python-${PYTHON_VERSION}.tgz

# build python and remove left-over sources
RUN cd /opt/Python-${PYTHON_VERSION} \
    && ./configure --prefix=/usr --enable-optimizations --with-ensurepip=install \
    && make install \
    && rm /opt/Python-${PYTHON_VERSION}.tgz /opt/Python-${PYTHON_VERSION} -rf

# install google cloud cli for gsutil to rsync models
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update -y && apt-get install -y google-cloud-cli


RUN apt-get clean -y && rm -rf /var/lib/apt/lists/*

# install poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 - && \
    cd /usr/local/bin && \
    ln -s /etc/poetry/bin/poetry

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry install $(if [ "$PROD_ENV" = "production" ]; then echo --only main; fi) --no-interaction --no-ansi

RUN if [ "$COMPUTE_KERNEL" = "gpu" ]; then \
    poetry run poe install_cuda_libs \
    ; else \
    poetry run poe install_ml_cpu_libs \
    ; fi

COPY src /app

ENTRYPOINT [ "/bin/bash" , "-c"]