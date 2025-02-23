# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /backendim-brain ./cmd/server

# Runtime stage
FROM alpine:3.19
WORKDIR /app

# Switch to root before installing packages
USER root

# Install core dependencies
RUN apk add --no-cache \
  ca-certificates \
  curl \
  python3 \
  py3-pip \
  git \
  bash \
  jq \
  libc6-compat

# Install security tools
RUN apk add --no-cache --virtual .security-deps \
  openssl \
  libcrypto3

# Security hardening
RUN adduser -D -u 1001 backenduser && \
    mkdir -p /home/backenduser/.kube/azure /home/backenduser/.kube/manual && \
    chmod 0755 /home/backenduser && \
    chown -R backenduser:backenduser /home/backenduser/.kube

# Install dependencies for psutil
RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

# Install Azure CLI, kubectl
COPY scripts/install-awscli.sh scripts/install-kubectl.sh /tmp/
RUN /tmp/install-awscli.sh && \
  /tmp/install-kubectl.sh && \
  rm -f /tmp/install-*.sh && \
  rm -rf /var/cache/apk/*

# Ensure Kubernetes config file is generated properly
RUN touch /home/backenduser/.kube/azure/config && \
    chmod 600 /home/backenduser/.kube/azure/config && \
    chown backenduser:backenduser /home/backenduser/.kube/azure/config

# Fetch AKS credentials on container start
RUN az aks get-credentials --resource-group myResourceGroup --name myAKSCluster --overwrite-existing

# Application setup
COPY --from=builder /backendim-brain .
COPY scripts/ ./scripts/
COPY deployments/ ./deployments/

# Security hardening
RUN find ./scripts/ -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod 0755 {} + && \
  mkdir -p /home/backenduser/.kube/azure /home/backenduser/.kube/manual && \
  chmod 0755 /home/backenduser && \
  chown -R backenduser:backenduser /app /home/backenduser/.kube/azure /home/backenduser/.kube/manual && \
  chmod 0700 /home/backenduser/.kube

# Set environment variables for Azure
ENV KUBECONFIG=/home/backenduser/.kube/config \
  AZURE_CONFIG_DIR=/home/backenduser/.azure \
  PATH="/app/scripts:${PATH}" \
  GIT_SSL_NO_VERIFY="false"

USER backenduser

HEALTHCHECK --interval=30s --timeout=3s CMD scripts/healthcheck.sh
ENTRYPOINT ["/app/scripts/kube-init.sh", "--"]
CMD ["./backendim-brain"]