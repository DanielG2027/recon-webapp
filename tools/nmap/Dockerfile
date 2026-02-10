# Pinned Nmap for recon-only scanning (no exploit scripts)
FROM alpine:3.19
RUN apk add --no-cache nmap nmap-scripts
# Default: run nmap (override with command)
ENTRYPOINT ["nmap"]
CMD ["--version"]
