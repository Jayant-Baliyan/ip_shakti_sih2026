# Phase 20: Deployment Architecture

## 1. Overview

This document defines the deployment architecture for IP-SAKTI Sahayak, covering local development, staging, and production environments with infrastructure-as-code, container orchestration, and environment promotion strategies.

### 1.1 Design Principles

1. **Environment Parity**: Dev/staging/prod as similar as possible
2. **Infrastructure as Code**: All infrastructure version-controlled and reproducible
3. **Immutable Deployments**: Blue-green or rolling deployments with rollback
4. **Observability First**: Built-in monitoring, logging, tracing
5. **Security by Default**: Network policies, secrets management, least privilege
6. **Cost Awareness**: Right-sizing, auto-scaling, spot instances where appropriate
7. **Multi-region Ready**: Architecture supports geo-distribution

### 1.2 Deployment Targets

| Environment | Purpose | Infrastructure | Scale |
|-------------|---------|----------------|-------|
| **Local** | Development, testing | Docker Compose / Kind | Single node |
| **CI/CD** | Automated testing | GitHub Actions / GitLab CI | Ephemeral |
| **Staging** | Pre-production validation | Kubernetes (dev cluster) | 10% prod |
| **Production** | Live traffic | Kubernetes (multi-AZ) | Full scale |
| **DR** | Disaster recovery | Kubernetes (different region) | Warm standby |

---

## 2. Container Architecture

### 2.1 Service Containers

```dockerfile
# Dockerfile.base - Base image for all services
FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

```dockerfile
# Dockerfile.api - API Gateway service
FROM base AS api

COPY --chown=appuser:appuser ./services/api /app
COPY --chown=appuser:appuser ./shared /app/shared

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```dockerfile
# Dockerfile.retrieval - Retrieval service (GPU)
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 AS retrieval-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.retrieval.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.retrieval.txt

USER appuser
WORKDIR /app
COPY --chown=appuser:appuser ./services/retrieval /app
COPY --chown=appuser:appuser ./shared /app/shared

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 2.2 Service Definitions

```yaml
# docker-compose.yml (Local Development)
version: '3.8'

services:
  # Infrastructure
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ip_sakti
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes: [redis_data:/data]
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes: [minio_data:/data]
    ports: ["9000:9000", "9001:9001"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  falkordb:
    image: falkordb/falkordb:latest
    volumes: [falkordb_data:/data]
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "-p", "6379", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Application Services
  api-gateway:
    build:
      context: .
      dockerfile: services/api-gateway/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
      - FALKORDB_URL=redis://falkordb:6379
      - JWT_PRIVATE_KEY=${JWT_PRIVATE_KEY}
      - LOG_LEVEL=DEBUG
    ports: ["8000:8000"]
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
      minio: {condition: service_healthy}
      falkordb: {condition: service_healthy}

  query-service:
    build:
      context: .
      dockerfile: services/query-service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - FALKORDB_URL=redis://falkordb:6379
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=gpt-4o-mini
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  retrieval-service:
    build:
      context: .
      dockerfile: services/retrieval-service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - VECTOR_DB_PATH=/data/vectors
      - EMBEDDING_MODEL=bge-m3
    volumes:
      - vector_data:/data/vectors
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  formulation-service:
    build:
      context: .
      dockerfile: services/formulation-service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - FALKORDB_URL=redis://falkordb:6379

  jurisdiction-service:
    build:
      context: .
      dockerfile: services/jurisdiction-service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - FALKORDB_URL=redis://falkordb:6379

  ingestion-service:
    build:
      context: .
      dockerfile: services/ingestion-service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
      - MINIO_BUCKET=documents
    volumes:
      - ./data/corpus:/data/corpus:ro

  evaluation-service:
    build:
      context: .
      dockerfile: services/evaluation-service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ip_sakti
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=http://clickhouse:8123

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
      - grafana_data:/var/lib/grafana
    ports: ["3000:3000"]
    depends_on: [prometheus]

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686", "6831:6831/udp", "14268:14268"]
    environment:
      - COLLECTOR_OTLP_ENABLED=true

volumes:
  postgres_data:
  redis_data:
  minio_data:
  falkordb_data:
  vector_data:
  prometheus_data:
  grafana_data:
```

---

## 3. Kubernetes Deployment (Production)

### 3.1 Namespace Structure

```yaml
# kubernetes/namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ip-sakti-system
  labels:
    name: ip-sakti-system
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: ip-sakti-apps
  labels:
    name: ip-sakti-apps
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: ip-sakti-data
  labels:
    name: ip-sakti-data
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: ip-sakti-monitoring
  labels:
    name: ip-sakti-monitoring
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: ip-sakti-infra
  labels:
    name: ip-sakti-infra
    environment: production
```

### 3.2 Core Service Deployments

```yaml
# kubernetes/services/api-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: ip-sakti-apps
  labels:
    app: api-gateway
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: api-gateway
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: api-gateway
        image: ghcr.io/ip-sakti/api-gateway:v1.2.3
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: JWT_PRIVATE_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-keys
              key: private-key
        - name: LOG_LEVEL
          value: "INFO"
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values: [api-gateway]
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: ip-sakti-apps
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP
```

### 3.3 GPU Workloads (Retrieval, Reranker)

```yaml
# kubernetes/services/retrieval-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: retrieval-service
  namespace: ip-sakti-apps
spec:
  replicas: 2
  selector:
    matchLabels:
      app: retrieval-service
  template:
    metadata:
      labels:
        app: retrieval-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8001"
    spec:
      serviceAccountName: retrieval-service
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: retrieval-service
        image: ghcr.io/ip-sakti/retrieval-service:v1.2.3
        imagePullPolicy: Always
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: VECTOR_DB_PATH
          value: "/data/vectors"
        - name: EMBEDDING_MODEL
          value: "bge-m3"
        resources:
          requests:
            cpu: "2000m"
            memory: "8Gi"
            nvidia.com/gpu: 1
          limits:
            cpu: "4000m"
            memory: "16Gi"
            nvidia.com/gpu: 1
        volumeMounts:
        - name: vector-storage
          mountPath: /data/vectors
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 60
          periodSeconds: 30
      volumes:
      - name: vector-storage
        persistentVolumeClaim:
          claimName: vector-pvc
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vector-pvc
  namespace: ip-sakti-data
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: "fast-ssd"
  resources:
    requests:
      storage: 500Gi
```

### 3.4 Stateful Services (PostgreSQL, Redis, FalkorDB)

```yaml
# kubernetes/data/postgresql.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgresql
  namespace: ip-sakti-data
spec:
  instances: 3
  imageName: ghcr.io/cloudnative-pg/postgresql:16.2
  primaryUpdateStrategy: unsupervised
  replicationSlots:
    highAvailability:
      enabled: true
      syncReplicas: 1
  bootstrap:
    initdb:
      database: ip_sakti
      owner: postgres
      secret:
        name: postgresql-credentials
  storage:
    size: 200Gi
    storageClass: fast-ssd
  resources:
    requests:
      cpu: "2000m"
      memory: "8Gi"
    limits:
      cpu: "4000m"
      memory: "16Gi"
  monitoring:
    enabled: true
    prometheus:
      port: 9187
  backup:
    barmanObjectStore:
      destinationPath: s3://ip-sakti-backups/postgresql
      endpointURL: https://s3.amazonaws.com
      s3Credentials:
        accessKeyId:
          name: backup-credentials
          key: ACCESS_KEY
        secretAccessKey:
          name: backup-credentials
          key: SECRET_KEY
    retentionPolicy: "30d"
    schedule: "0 2 * * *"
  networkAttachments:
  - name: pg-network
```

```yaml
# kubernetes/data/redis.yaml
apiVersion: redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: redis
  namespace: ip-sakti-data
spec:
  clusterSize: 6
  redisExporter:
    enabled: true
    image: oliver006/redis_exporter:v1.55.0
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: fast-ssd
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
  resources:
    requests:
      cpu: "1000m"
      memory: "4Gi"
    limits:
      cpu: "2000m"
      memory: "8Gi"
  redisConfig:
    maxmemory: "3gb"
    maxmemory-policy: "allkeys-lru"
    appendonly: "yes"
```

---

## 4. Ingress & Networking

### 4.1 Ingress Controller

```yaml
# kubernetes/networking/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ip-sakti-ingress
  namespace: ip-sakti-apps
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';";
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.ip-sakti.in
    - app.ip-sakti.in
    secretName: ip-sakti-tls
  rules:
  - host: api.ip-sakti.in
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 80
      - path: /health
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 80
  - host: app.ip-sakti.in
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

### 4.2 Service Mesh (Istio)

```yaml
# kubernetes/istio/peer-authentication.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: ip-sakti-apps
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: api-gateway-authz
  namespace: ip-sakti-apps
spec:
  selector:
    matchLabels:
      app: api-gateway
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/istio-system/sa/ingressgateway"]
  - to:
    - operation:
        paths: ["/health", "/ready", "/metrics"]
      # Allow unauthenticated health checks
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: retrieval-service-dr
  namespace: ip-sakti-apps
spec:
  host: retrieval-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    loadBalancer:
      simple: LEAST_REQUEST
    circuitBreaker:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
```

---

## 5. Configuration Management

### 5.1 ConfigMaps & Secrets

```yaml
# kubernetes/config/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ip-sakti-config
  namespace: ip-sakti-apps
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  EMBEDDING_MODEL: "bge-m3"
  RERANKER_MODEL: "bge-reranker-v2-m3"
  RETRIEVAL_TOP_K: "100"
  RERANK_TOP_K: "20"
  FINAL_TOP_K: "12"
  RRF_K: "60"
  MMR_LAMBDA: "0.7"
  AUTHORITY_TIER_WEIGHTS: '{"1": 1.0, "2": 0.8, "3": 0.6, "4": 0.4}'
  CITATION_STYLE: "detailed"
  MAX_TOKENS: "4096"
  GENERATION_TEMPERATURE: "0.1"
  ABSTENTION_THRESHOLD: "0.4"
  ESCALATION_THRESHOLD: "0.6"
---
apiVersion: v1
kind: Secret
metadata:
  name: database-credentials
  namespace: ip-sakti-system
type: Opaque
stringData:
  url: "postgresql://postgres:password@postgresql-rw.ip-sakti-data:5432/ip_sakti"
---
apiVersion: v1
kind: Secret
metadata:
  name: jwt-keys
  namespace: ip-sakti-system
type: Opaque
stringData:
  private-key: |
    -----BEGIN PRIVATE KEY-----
    ...
    -----END PRIVATE KEY-----
  public-key: |
    -----BEGIN PUBLIC KEY-----
    ...
    -----END PUBLIC KEY-----
```

### 5.2 External Secrets (Secrets Operator)

```yaml
# kubernetes/config/external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: ip-sakti-system
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: ip-sakti-system
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
  data:
  - secretKey: url
    remoteRef:
      key: prod/ip-sakti/database
      property: url
  - secretKey: password
    remoteRef:
      key: prod/ip-sakti/database
      property: password
```

---

## 6. CI/CD Pipeline

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yaml
name: Deploy

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .[test]
      - name: Run unit tests
        run: pytest tests/unit -v --cov=src --cov-fail-under=80
      - name: Run integration tests
        run: pytest tests/integration -v
      - name: Run security tests
        run: pytest tests/security -v
      - name: Type checking
        run: mypy src/
      - name: Linting
        run: ruff check src/

  build:
    name: Build & Push
    needs: test
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push API Gateway
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/api-gateway/Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/api-gateway:${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push Retrieval Service
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/retrieval-service/Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/retrieval-service:${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # ... other services

  deploy-staging:
    name: Deploy to Staging
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure kubectl
        uses: azure/k8s-set-context@v1
        with:
          kubeconfig: ${{ secrets.STAGING_KUBECONFIG }}
      
      - name: Deploy to Staging
        run: |
          kubectl set image deployment/api-gateway \
            api-gateway=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/api-gateway:${{ github.sha }} \
            -n ip-sakti-apps
          # ... other services
      
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/api-gateway -n ip-sakti-apps --timeout=300s
      
      - name: Run smoke tests
        run: |
          pytest tests/smoke --base-url=https://staging-api.ip-sakti.in

  deploy-production:
    name: Deploy to Production
    needs: build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure kubectl
        uses: azure/k8s-set-context@v1
        with:
          kubeconfig: ${{ secrets.PROD_KUBECONFIG }}
      
      - name: Blue-Green Deploy
        run: |
          # Deploy to green namespace
          kubectl apply -k kubernetes/overlays/production-green
          
          # Run smoke tests against green
          pytest tests/smoke --base-url=https://green-api.ip-sakti.in
          
          # Switch traffic
          kubectl patch ingress ip-sakti-ingress -n ip-sakti-apps \
            -p '{"spec":{"rules":[{"host":"api.ip-sakti.in","http":{"paths":[{"path":"/v1","pathType":"Prefix","backend":{"service":{"name":"api-gateway-green","port":{"number":80}}}]}}]}}'
          
          # Wait and verify
          sleep 60
          pytest tests/smoke --base-url=https://api.ip-sakti.in
          
          # Cleanup blue
          kubectl delete namespace ip-sakti-apps-blue
```

---

## 7. Database Migrations

```python
# migrations/env.py (Alembic)
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

config = context.config
fileConfig(config.config_file_name)

target_metadata = None  # Set to your models' metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```yaml
# kubernetes/jobs/migration.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration-{{ .Chart.AppVersion }}
  namespace: ip-sakti-system
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: migration
        image: ghcr.io/ip-sakti/migration-runner:v1.2.3
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

---

## 8. Backup & Disaster Recovery

### 8.1 Backup Strategy

| Component | Frequency | Retention | Method | RPO | RTO |
|-----------|-----------|-----------|--------|-----|-----|
| PostgreSQL | Daily + WAL | 30 days | pgBackRest to S3 | <1 min | <30 min |
| Redis | Daily RDB | 7 days | Redis snapshot to S3 | <1 hour | <15 min |
| Vector DB | Weekly | 4 weeks | File copy to S3 | <1 week | <2 hours |
| Graph DB | Daily | 30 days | FalkorDB backup to S3 | <1 day | <1 hour |
| Object Storage | Continuous | 90 days | Versioning + Cross-region replication | 0 | <1 hour |
| Kubernetes Configs | On change | Indefinite | GitOps (ArgoCD) | 0 | <15 min |

### 8.2 Disaster Recovery Plan

```yaml
# dr/plan.yaml
dr_plan:
  # Recovery Time Objectives
  rto:
    critical_services: 30min  # API, Query, Retrieval
    data_services: 2hr        # PostgreSQL, Vector DB
    analytics: 4hr            # ClickHouse, Grafana
  
  # Recovery Point Objectives
  rpo:
    transactional: 1min       # PostgreSQL (synchronous replication)
    cache: 1hr                # Redis (async replication)
    vectors: 24hr             # Vector index (rebuildable)
    graph: 24hr               # Graph DB (rebuildable)
  
  # Failover Procedure
  failover:
    1: "Detect primary region failure (health checks, alerts)"
    2: "Activate DR DNS records (Route53 failover)"
    3: "Promote DR PostgreSQL replica to primary"
    4: "Scale up DR Kubernetes cluster (HPA / cluster autoscaler)"
    5: "Restore Redis from latest snapshot"
    6: "Rebuild vector index from PostgreSQL (parallel)"
    7: "Verify all services healthy"
    8: "Notify stakeholders"
  
  # Fallback Procedure
  fallback:
    1: "Verify primary region restored"
    2: "Sync data from DR to primary (if needed)"
    3: "Switch DNS back to primary"
    4: "Scale down DR cluster"
    5: "Post-incident review"
```

---

## 9. Scaling Strategy

### 9.1 Horizontal Pod Autoscaler

```yaml
# kubernetes/autoscaling/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: ip-sakti-apps
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

### 9.2 Cluster Autoscaler

```yaml
# kubernetes/autoscaling/cluster-autoscaler.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
  namespace: kube-system
data:
  scale-down-unneeded-time: "10m"
  scale-down-utilization-threshold: "0.5"
  scale-down-gpu-utilization-threshold: "0.3"
  max-node-provision-time: "15m"
  scan-interval: "10s"
---
# Node groups for different workloads
node_groups:
  - name: general
    instance_type: m6i.xlarge
    min_size: 3
    max_size: 20
    labels:
      workload: general
    taints: []
  
  - name: gpu
    instance_type: g5.xlarge
    min_size: 0
    max_size: 10
    labels:
      workload: gpu
      nvidia.com/gpu: "true"
    taints:
    - key: nvidia.com/gpu
      effect: NoSchedule
  
  - name: memory
    instance_type: r6i.xlarge
    min_size: 0
    max_size: 5
    labels:
      workload: memory
    taints: []
```

---

## 10. Cost Optimization

### 10.1 Resource Optimization

```python
class CostOptimizer:
    """Continuous cost optimization recommendations."""
    
    def analyze(self) -> CostOptimizationReport:
        recommendations = []
        
        # Right-sizing
        for deployment in self.get_deployments():
            usage = self.get_resource_usage(deployment)
            if usage.cpu_avg < 0.3:
                recommendations.append(Recommendation(
                    type="rightsize_cpu",
                    resource=deployment.name,
                    current=f"{deployment.cpu_request} CPU",
                    suggested=f"{max(usage.cpu_avg * 1.5, 0.1):.1f} CPU",
                    monthly_savings=self._calculate_savings(deployment, "cpu")
                ))
        
        # Spot instances for fault-tolerant workloads
        for node_group in self.get_node_groups():
            if node_group.workload in ["batch", "eval", "ingestion"]:
                recommendations.append(Recommendation(
                    type="spot_instances",
                    resource=node_group.name,
                    current="On-demand",
                    suggested="Spot (with fallback)",
                    monthly_savings=node_group.monthly_cost * 0.7
                ))
        
        # Idle resource detection
        idle_resources = self.detect_idle_resources()
        for resource in idle_resources:
            recommendations.append(Recommendation(
                type="remove_idle",
                resource=resource.name,
                current=f"Running (${resource.monthly_cost}/mo)",
                suggested="Stop/Delete",
                monthly_savings=resource.monthly_cost
            ))
        
        return CostOptimizationReport(
            total_monthly_cost=self.get_total_cost(),
            potential_savings=sum(r.monthly_savings for r in recommendations),
            recommendations=recommendations
        )
```

---

## 11. Environment Promotion

### 11.1 Promotion Gates

| Gate | Local → CI | CI → Staging | Staging → Prod |
|------|------------|--------------|----------------|
| Unit Tests | ✅ Required | ✅ Required | ✅ Required |
| Integration Tests | ❌ | ✅ Required | ✅ Required |
| Security Scan | ✅ Required | ✅ Required | ✅ Required |
| Performance Benchmarks | ❌ | ✅ (sample) | ✅ Required |
| Evaluation Suite | ❌ | ❌ | ✅ Required |
| Manual Approval | ❌ | ❌ | ✅ Required |
| Canary Deployment | ❌ | ❌ | ✅ (10% → 100%) |
| Rollback Verification | ❌ | ✅ | ✅ |

### 11.2 ArgoCD Application

```yaml
# argocd/applications.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ip-sakti-production
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/ip-sakti/infrastructure
    targetRevision: main
    path: kubernetes/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: ip-sakti-apps
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas
  - group: ""
    kind: Secret
    jsonPointers:
    - /data
```

---

## 12. Open Research Questions

| ID | Question | Priority |
|----|----------|----------|
| ORQ-90 | Optimal GPU sharing strategy for multi-model inference? | High |
| ORQ-91 | Serverless vs Kubernetes for bursty evaluation workloads? | Medium |
| ORQ-92 | Multi-region active-active for global latency? | Medium |
| ORQ-93 | Cost-optimal vector index storage tiering (hot/warm/cold)? | High |
| ORQ-94 | GitOps vs traditional CI/CD for ML model deployments? | Medium |

---

## 13. Implementation Checklist

- [ ] Dockerfiles for all services (multi-stage, distroless)
- [ ] Docker Compose for local development
- [ ] Kubernetes manifests (base + overlays per environment)
- [ ] Helm charts for stateful services (PostgreSQL, Redis, FalkorDB)
- [ ] Network policies (zero-trust)
- [ ] Service mesh (Istio) configuration
- [ ] Ingress controller (NGINX) with TLS
- [ ] Cert-manager for certificate management
- [ ] External Secrets Operator
- [ ] ConfigMaps for non-secret configuration
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Automated testing in pipeline
- [ ] Security scanning in pipeline
- [ ] Blue-green deployment strategy
- [ ] Database migration jobs
- [ ] Backup configuration (pgBackRest, Velero)
- [ ] Disaster recovery runbooks
- [ ] HPA for all services
- [ ] Cluster autoscaler with GPU nodes
- [ ] Cost monitoring and optimization
- [ ] ArgoCD for GitOps
- [ ] Environment promotion gates
- [ ] Runbooks for common operations