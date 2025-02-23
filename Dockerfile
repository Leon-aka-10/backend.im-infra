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
RUN adduser -D -u 1001 azureuser && \
    mkdir -p /home/azureuser/.kube/azure /home/azureuser/.kube/manual && \
    chmod 0755 /home/azureuser && \
    chown -R azureuser:azureuser /home/azureuser/.kube

# Install dependencies for psutil
RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

# Install Azure CLI, kubectl
COPY scripts/install-awscli.sh scripts/install-kubectl.sh /tmp/
RUN /tmp/install-awscli.sh && \
  /tmp/install-kubectl.sh && \
  rm -f /tmp/install-*.sh && \
  rm -rf /var/cache/apk/*

# Ensure Kubernetes config file is generated properly
RUN mkdir -p /home/azureuser/.kube/azure && \
    touch /home/azureuser/.kube/azure/config && \
    chmod 600 /home/azureuser/.kube/azure/config && \
    chown azureuser:azureuser /home/azureuser/.kube/azure/config && \
    az aks get-credentials --resource-group myResourceGroup --name myAKSCluster --file /home/azureuser/.kube/azure/config --overwrite-existing

# Application setup
COPY --from=builder /backendim-brain .
COPY scripts/ ./scripts/
COPY deployments/ ./deployments/

# Security hardening
RUN find ./scripts/ -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod 0755 {} + && \
  mkdir -p /home/azureuser/.kube/azure /home/azureuser/.kube/manual && \
  chmod 0755 /home/azureuser && \
  chown -R azureuser:azureuser /app /home/azureuser/.kube/azure /home/azureuser/.kube/manual && \
  chmod 0700 /home/azureuser/.kube

# Set environment variables for Azure
ENV KUBECONFIG=/home/azureuser/.kube/config \
  AZURE_CONFIG_DIR=/home/azureuser/.azure \
  PATH="/app/scripts:${PATH}" \
  GIT_SSL_NO_VERIFY="false"

USER azureuser

HEALTHCHECK --interval=30s --timeout=3s CMD scripts/healthcheck.sh
ENTRYPOINT ["/app/scripts/kube-init.sh", "--"]
CMD ["./backendim-brain"]