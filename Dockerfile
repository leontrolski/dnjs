FROM golang:1.16.0-buster
WORKDIR /src/dnjs-go
COPY dnjs-go .
RUN ./build  # caches required modules
