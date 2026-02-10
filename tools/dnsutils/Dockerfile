# dig, nslookup for DNS discovery
FROM alpine:3.19
RUN apk add --no-cache bind-tools
ENTRYPOINT ["dig"]
CMD ["--version"]
