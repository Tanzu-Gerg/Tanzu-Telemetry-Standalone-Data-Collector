FROM ubuntu:xenial-20210804
RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install python3.5
WORKDIR /tmp
USER root
COPY ./tanzu-telemetry-standalone-data-collector.py ./
COPY ./test.sh ./
COPY ./cf ./
ENV PATH="$PATH:/tmp"
ENV CF_API api.example.com
ENV CF_USER admin
ENV CF_PASSWORD password
# CMD ["sleep", "100"]
CMD ["test.sh"]
