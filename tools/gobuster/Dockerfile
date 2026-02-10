# Directory/file discovery - gobuster or similar
FROM golang:1.22-alpine AS build
RUN apk add --no-cache git
RUN go install github.com/OJ/gobuster/v3@latest

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
COPY --from=build /go/bin/gobuster /usr/local/bin/gobuster
ENTRYPOINT ["gobuster"]
CMD ["--help"]
