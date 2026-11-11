FROM python:3.12-slim AS john-build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config libssl-dev zlib1g-dev libgmp-dev curl ca-certificates && rm -rf /var/lib/apt/lists/*
ARG JOHN_REVISION=37bebbe4b6442c8dd3888e5848ef062c0783e9f3
RUN mkdir /john && curl -fL --retry 3 https://codeload.github.com/openwall/john/tar.gz/${JOHN_REVISION} | tar -xz -C /john --strip-components=1
RUN cd /john/src && ./configure --disable-openmp --disable-opencl --disable-native-tests && make -s -j2

FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN echo 'wireshark-common wireshark-common/install-setuid boolean false' | debconf-set-selections && apt-get update && apt-get install -y --no-install-recommends bash passwd util-linux procps curl xxd file binutils less zip unzip grep findutils libimage-exiftool-perl tshark binwalk libgmp10 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=john-build /john/run /opt/john
COPY --from=john-build /john/doc /usr/share/doc/john
RUN /opt/john/john --list=formats | grep -q 'Raw-SHA256'
COPY apps/crack4fun/sandbox/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/crack4fun/sandbox/prepare_wordlist.py /tmp/prepare_wordlist.py
RUN python /tmp/prepare_wordlist.py && rm /tmp/prepare_wordlist.py
RUN useradd --uid 1000 --create-home --shell /bin/bash apprentice && mkdir /work /evidence /state && chown apprentice:apprentice /work && chmod 700 /root
COPY apps/crack4fun/sandbox/john-wrapper.py /usr/local/bin/john
RUN chmod 755 /usr/local/bin/john
WORKDIR /agent
COPY apps/crack4fun/sandbox/agent.py apps/crack4fun/sandbox/artifacts.py ./
CMD ["python", "agent.py"]
