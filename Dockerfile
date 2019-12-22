FROM python:3.6-alpine

WORKDIR /usr/local/ipfs-gwx

RUN apk update
RUN apk add git

# Install dependencies.
ADD requirements.txt /usr/local/ipfs-gwx
RUN cd /usr/local/ipfs-gwx && pip install -r requirements.txt

# Copy the application and config
COPY bin/ipfs-gwx /usr/local/bin/ipfs-gwx
COPY ipfsgwx/ /usr/local/ipfs-gwx/ipfsgwx
COPY examples/ipfs-gwx.docker.conf /usr/local/ipfs-gwx

EXPOSE 80

ENV PYTHONPATH /usr/local/ipfs-gwx
ENTRYPOINT ["/usr/local/bin/ipfs-gwx", "-d", "--config", \
	    "/usr/local/ipfs-gwx/ipfs-gwx.docker.conf", \
	    "--ipfsapihost", "ipfs"]
