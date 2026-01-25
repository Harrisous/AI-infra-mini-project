# AI Infrastructure Mini Project

A Kubernetes-based model serving system with hot model reload capability. This project demonstrates a production-ready infrastructure for serving Large Language Models (LLMs) with zero-downtime model updates, synchronized across multiple replicas.

## Overview

This project implements a distributed inference system that allows you to:
- Serve LLM inference requests across multiple replicas
- Hot-swap models without restarting servers
- Synchronize model updates across all replicas
- Monitor model versions and status in real-time
- Deploy on Kubernetes with GPU support

The system consists of three main components:
1. **Inference Server Cluster**: Multiple replicas serving LLM inference with hot model reload
2. **Trainer Server**: Simulates training workflow by sending prompts and requesting model updates
3. **UI Server**: Web interface for monitoring and interacting with the system

## Key Features

- **Hot Model Reload**: Update models without server restart
- **Model Version Tracking**: Track model versions in response headers
- **Synchronized Updates**: Coordinate updates across multiple replicas
- **Zero-Downtime Swaps**: Serve requests during model updates
- **Error Handling**: Graceful degradation and error recovery
- **Health Checks**: Liveness and readiness probes for Kubernetes
- **GPU Support**: Automatic GPU detection and utilization
- **Shared Storage**: Persistent model cache across replicas
- **Local & K8s Deployment**: Run locally or deploy to Kubernetes

## Project Structure

```
AI-infra-mini-project/
├── inference-server/          # Inference server implementation
│   ├── server.py              # FastAPI application and endpoints
│   ├── model_manager.py       # Model loading, hot swap, version tracking
│   ├── version_tracker.py     # Model version and repo ID tracking
│   ├── sync_coordinator.py    # File-based synchronization for K8s
│   └── schemas.py             # Pydantic models for API
│
├── trainer-server/            # Trainer server implementation
│   └── trainer.py             # Training simulation and orchestration
│
├── ui-server/                 # Web UI server
│   ├── app.py                 # FastAPI UI server
│   └── templates/
│       └── index.html         # Web interface
│
├── k8s/                       # Kubernetes manifests
│   ├── storage.yaml           # PersistentVolumeClaim for model cache
│   ├── config.yaml            # ConfigMaps for configuration
│   ├── inference-deployment.yaml  # Inference server deployment
│   ├── inference-service.yaml     # Inference service (load balancer)
│   ├── inference-headless-service.yaml  # Headless service for pod discovery
│   ├── trainer-deployment.yaml    # Trainer deployment
│   ├── trainer-service.yaml       # Trainer service
│   ├── ui-deployment.yaml         # UI deployment
│   ├── ui-service.yaml            # UI service
│   ├── deploy.sh                  # Deployment script
│   └── discover-pods.sh           # Pod discovery utility
│
├── docker/                    # Dockerfiles
│   ├── inference-server.Dockerfile
│   ├── trainer-server.Dockerfile
│   └── ui-server.Dockerfile
│
├── scripts/                    # Utility scripts
│   ├── run_local.sh           # Run locally (2 inference servers + trainer)
│   ├── run_with_ui.sh         # Run locally with UI
│   ├── build_images.sh        # Build Docker images
│   ├── deploy.sh              # Deploy to Kubernetes
│   ├── setup_minikube.sh      # Setup minikube for local K8s
│   └── test.sh                # Test script
│
├── docs/                      # Documentation
│   ├── README.md              # Documentation index
│   ├── ARCHITECTURE.md        # System architecture details
│   ├── SETUP.md               # Setup guide
│   └── API.md                 # API documentation
│
├── eks-cluster.yaml           # EKS cluster configuration (eksctl)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **CUDA 12.4+** (for GPU support)
- **Docker** (for containerized deployment)
- **Kubernetes cluster** or **minikube** (for K8s deployment)
- **16GB+ GPU memory** (for 7B-8B models)
- **AWS CLI** and **eksctl** (for AWS EKS deployment)

### Local Development

1. **Clone and setup environment:**
   ```bash
   cd AI-infra-mini-project
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip setuptools wheel
   ```

2. **Install PyTorch (GPU):**
   ```bash
   pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run local simulation:**
   ```bash
   ./scripts/run_local.sh
   ```

   This will:
   - Start 2 inference servers on ports 8001 and 8002
   - Wait for models to load
   - Run trainer simulation that sends prompts and requests model updates

5. **Run with UI (optional):**
   ```bash
   ./scripts/run_with_ui.sh
   ```
   Then open `http://localhost:8080` in your browser.

### Manual Local Start

If you prefer to start components manually:

```bash
# Terminal 1: Inference server 1
export HF_HOME=./models/hf_home
export INITIAL_MODEL_REPO_ID=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
PYTHONPATH=./inference-server python -m uvicorn server:app --host 0.0.0.0 --port 8001

# Terminal 2: Inference server 2
export HF_HOME=./models/hf_home
export INITIAL_MODEL_REPO_ID=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
PYTHONPATH=./inference-server python -m uvicorn server:app --host 0.0.0.0 --port 8002

# Terminal 3: Trainer
export INFERENCE_URLS=http://localhost:8001,http://localhost:8002
export INITIAL_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
export SUBSTITUTE_MODEL=Qwen/Qwen2.5-7B-Instruct
python -m trainer_server.trainer
```

## Kubernetes Deployment (Minikube)

### 1. Build Docker Images

```bash
./scripts/build_images.sh
```

This builds:
- `inference-server:latest`
- `trainer-server:latest`
- `ui-server:latest`

### 2. Setup Minikube

```bash
./scripts/setup_minikube.sh
```

This will:
- Start minikube if not running
- Enable storage provisioner
- Load Docker images into minikube

### 3. Deploy to Kubernetes

```bash
cd k8s
./deploy.sh
```

Or deploy to a specific namespace:
```bash
./deploy.sh my-namespace
```

### 4. Check Status

```bash
kubectl get pods
kubectl get services
kubectl logs -l app=inference-server
kubectl logs -l app=trainer-server
kubectl logs -l app=ui-server
```

### 5. Access Services

**UI Server:**
```bash
kubectl port-forward svc/ui-service 8080:80
# Open http://localhost:8080
```

**Inference Service:**
```bash
kubectl port-forward svc/inference-service 8000:8000
# Test: curl http://localhost:8000/healthz
```

## Configuration

### Environment Variables

**Inference Server:**
- `HF_HOME`: HuggingFace cache directory (default: `~/.cache/huggingface`)
- `TRANSFORMERS_CACHE`: Transformers cache directory
- `INITIAL_MODEL_REPO_ID`: Initial model to load (e.g., `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`)
- `SYNC_STATE_FILE`: Optional file path for file-based synchronization (e.g., `/models/sync_state.json`)

**Trainer Server:**
- `INFERENCE_URLS`: Comma-separated list of inference server URLs
- `INITIAL_MODEL`: Initial model for trainer simulation
- `SUBSTITUTE_MODEL`: Model to switch to during simulation

**UI Server:**
- `INFERENCE_URLS`: Comma-separated list of inference server URLs
- `TRAINER_URL`: Trainer server URL

### Model Selection

Default models:
- **Initial**: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- **Substitute**: `Qwen/Qwen2.5-7B-Instruct`

To use different models, set environment variables or update `k8s/config.yaml`:

```bash
export INITIAL_MODEL_REPO_ID=your-org/your-model-7b
export SUBSTITUTE_MODEL=your-org/your-model-8b
```

### Kubernetes Configuration

Edit `k8s/config.yaml` to change:
- Model repository IDs
- Cache paths
- Service URLs
- Resource limits

## API Documentation

The inference server exposes the following endpoints:

- `GET /healthz` - Health check
- `GET /ready` - Readiness check (model loaded)
- `GET /status` - Current model status
- `POST /generate` - Generate text from prompt
- `POST /update-model` - Request hot model reload

See [docs/API.md](docs/API.md) for complete API documentation.

## Troubleshooting

### Model Loading Fails

- Check GPU memory: `nvidia-smi`
- Try smaller model or enable quantization
- Check HuggingFace Hub access: `curl https://huggingface.co/api/models/your-model`
- For private repos, set `HF_TOKEN` environment variable

### Inference Servers Not Ready

- Check logs: `kubectl logs -l app=inference-server`
- Check resources: `kubectl describe pod <pod-name>`
- Verify GPU access: `kubectl get nodes -o yaml | grep nvidia.com/gpu`
- Check PVC: `kubectl get pvc model-storage`

### Port Conflicts

- Change ports in `scripts/run_local.sh` or use different ports
- For K8s, ports are configured in service manifests

### Minikube Issues

- Restart minikube: `minikube delete && minikube start`
- Check addons: `minikube addons list`
- Use Docker driver: `minikube start --driver=docker`

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: System architecture and design decisions
- **[SETUP.md](docs/SETUP.md)**: Detailed setup guide
- **[API.md](docs/API.md)**: Complete API reference

## AWS EKS Deployment Plan

This section provides a comprehensive step-by-step guide for deploying the AI Infrastructure Mini Project on Amazon Elastic Kubernetes Service (EKS), based on real-world deployment experience.

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **WSL (Windows Subsystem for Linux)** or Linux environment
3. **Docker** installed and configured (Docker Desktop with WSL integration recommended)
4. **AWS CLI v2** installed
5. **kubectl** installed (1.27+)
6. **eksctl** installed (see installation below)

### Step 0: Local Build and Test

Before deploying to AWS, ensure your Docker images build and run locally:

```bash
# Build all three images
docker build -f docker/inference-server.Dockerfile -t inference-server:latest .
docker build -f docker/trainer-server.Dockerfile -t trainer-server:latest .
docker build -f docker/ui-server.Dockerfile -t ui-server:latest

# Verify images exist
docker images | grep server
```

### Step 1: Install and Configure AWS CLI (WSL/Linux)

**For WSL Ubuntu:**

```bash
# Update package list
sudo apt update
sudo apt install -y unzip curl

# Download AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

# Install
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

**Configure AWS credentials:**

1. In AWS Console, go to **IAM** → **Users** → Create or select a user
2. Go to **Security credentials** → **Create access key**
3. Choose **CLI / Command Line Interface** as the use case
4. Save the **Access Key ID** and **Secret Access Key** (you'll only see the secret once)

**Configure AWS CLI:**

```bash
aws configure
```

Enter:
- AWS Access Key ID: Your access key ID
- AWS Secret Access Key: Your secret access key
- Default region name: `us-east-1` (or your preferred region)
- Default output format: `json` or press Enter

**Verify configuration:**

```bash
aws sts get-caller-identity
```

You should see your Account ID, ARN, and User ID.

### Step 2: Setup IAM Permissions

Your IAM user needs comprehensive permissions to create and manage EKS clusters. Create an inline policy for your IAM user:

1. Go to **IAM** → **Users** → Select your user → **Permissions** → **Add inline policy**
2. Choose **JSON** tab and paste the following policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EksFullAccess",
      "Effect": "Allow",
      "Action": "eks:*",
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationFullAccess",
      "Effect": "Allow",
      "Action": "cloudformation:*",
      "Resource": "*"
    },
    {
      "Sid": "Ec2FullForEksctl",
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*"
    },
    {
      "Sid": "IamForEksctlWithTagging",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:CreateInstanceProfile",
        "iam:DeleteInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:RemoveRoleFromInstanceProfile",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:ListRolePolicies",
        "iam:GetRolePolicy",
        "iam:TagRole",
        "iam:UntagRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IamServiceLinkedRoleForEks",
      "Effect": "Allow",
      "Action": "iam:CreateServiceLinkedRole",
      "Resource": "arn:aws:iam::*:role/aws-service-role/*"
    },
    {
      "Sid": "IamOIDCProviderForEks",
      "Effect": "Allow",
      "Action": [
        "iam:CreateOpenIDConnectProvider",
        "iam:GetOpenIDConnectProvider",
        "iam:TagOpenIDConnectProvider",
        "iam:DeleteOpenIDConnectProvider",
        "iam:ListOpenIDConnectProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AutoscalingForEksctl",
      "Effect": "Allow",
      "Action": "autoscaling:*",
      "Resource": "*"
    },
    {
      "Sid": "ELBForEksctl",
      "Effect": "Allow",
      "Action": "elasticloadbalancing:*",
      "Resource": "*"
    },
    {
      "Sid": "LogsAndCloudWatchForEksctl",
      "Effect": "Allow",
      "Action": [
        "logs:*",
        "cloudwatch:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GenericTaggingForEksctl",
      "Effect": "Allow",
      "Action": [
        "tag:GetResources",
        "tag:TagResources",
        "tag:UntagResources"
      ],
      "Resource": "*"
    }
  ]
}
```

3. Name the policy (e.g., `eksctl-lab-admin`) and click **Create policy**

**Note:** This policy is comprehensive for learning/development environments. For production, use more restrictive permissions following the principle of least privilege.

### Step 3: Install eksctl

**For WSL/Linux (recommended method):**

```bash
# Set architecture
ARCH=amd64
PLATFORM=$(uname -s)_$ARCH

# Download latest version
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"

# Extract to /tmp
tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp

# Install to /usr/local/bin
sudo install -m 0755 /tmp/eksctl /usr/local/bin

# Verify installation
eksctl version
```

**Alternative:** If you have the `eksctl_Linux_amd64.tar.gz` file in your project:

```bash
tar -xzf eksctl_Linux_amd64.tar.gz -C /tmp
sudo install -m 0755 /tmp/eksctl /usr/local/bin
eksctl version
```

### Step 4: Create ECR Repositories

**In AWS Console:**

1. Go to **ECR (Elastic Container Registry)** in AWS Console
2. Select your region (e.g., `us-east-1`)
3. Click **Private repositories** → **Create repository**
4. Create three repositories:
   - `ai-infra-inference`
   - `ai-infra-trainer`
   - `ai-infra-ui`
5. Note the repository URIs (format: `<account-id>.dkr.ecr.<region>.amazonaws.com/<repo-name>`)

**Or via CLI:**

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create repositories
aws ecr create-repository --repository-name ai-infra-inference --region $AWS_REGION
aws ecr create-repository --repository-name ai-infra-trainer --region $AWS_REGION
aws ecr create-repository --repository-name ai-infra-ui --region $AWS_REGION
```

### Step 5: Build and Push Docker Images to ECR

**Set up variables:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REGISTRY=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
```

**Login to ECR:**

```bash
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $REGISTRY
```

You should see `Login Succeeded`.

**Tag and push images:**

```bash
# Tag images
docker tag inference-server:latest $REGISTRY/ai-infra-inference:latest
docker tag trainer-server:latest $REGISTRY/ai-infra-trainer:latest
docker tag ui-server:latest $REGISTRY/ai-infra-ui:latest

# Push images
docker push $REGISTRY/ai-infra-inference:latest
docker push $REGISTRY/ai-infra-trainer:latest
docker push $REGISTRY/ai-infra-ui:latest
```

**Note:** If you get permission errors with `sudo docker`, add your user to the docker group:

```bash
sudo usermod -aG docker $USER
# Exit and restart your terminal, then retry without sudo
```

### Step 6: Update Kubernetes Manifests

Update the deployment files to use your ECR images:

**Update `k8s/inference-deployment.yaml`:**

Replace the image line with:
```yaml
image: <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-infra-inference:latest
```

**Update `k8s/trainer-deployment.yaml` and `k8s/ui-deployment.yaml`** similarly.

### Step 7: Check GPU Quota (Important)

Before creating the cluster, verify your GPU instance quota:

1. Go to **Service Quotas** in AWS Console
2. Select **Amazon Elastic Compute Cloud (Amazon EC2)**
3. Search for **"Running On-Demand G and VT instances"**
4. Check the **Applied quota value**

If it's 0, you need to request an increase:

1. Click **Request quota increase**
2. Request at least **16 vCPU** (for g4dn.xlarge: 4 vCPU per instance, max 2 instances = 8 vCPU, plus buffer)
3. Wait for approval (usually minutes to hours)

**Alternative:** If quota is 0 and you want to proceed, temporarily change GPU nodegroup to use `t3.large` in `eks-cluster.yaml` for testing.

### Step 8: Create EKS Cluster

**Review cluster configuration:**

```bash
cat eks-cluster.yaml
```

The configuration includes:
- Cluster name: `ai-infra-cluster`
- Region: `us-east-1`
- Kubernetes version: `1.29`
- CPU nodes: `t3.large` (2 desired, 1-3 range)
- GPU nodes: `g4dn.xlarge` (1 desired, 1-2 range) with label `role: gpu`

**Create the cluster:**

```bash
eksctl create cluster -f eks-cluster.yaml
```

This takes approximately 15-20 minutes. The command will:
- Create VPC, subnets, and security groups
- Create EKS control plane
- Create managed node groups
- Configure kubectl context automatically

**If you encounter "Stack already exists" error:**

```bash
# Delete the failed cluster first
eksctl delete cluster --name ai-infra-cluster --region us-east-1 --wait

# Or delete via CloudFormation console manually, then retry
```

**Verify cluster creation:**

```bash
kubectl get nodes
kubectl get nodes -l role=gpu  # Check GPU nodes
```

### Step 9: Install NVIDIA Device Plugin

GPU nodes require the NVIDIA device plugin:

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.16.1/deployments/static/nvidia-device-plugin.yml
```

**Verify GPU availability:**

```bash
kubectl get nodes -o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```

GPU nodes should show `1` in the GPU column.

### Step 10: Deploy Application to EKS

**Update storage configuration:**

Check available storage classes:
```bash
kubectl get storageclass
```

If using EBS (default), update `k8s/storage.yaml` to use `gp3` or `gp2` storage class. Note that EBS only supports `ReadWriteOnce`, not `ReadWriteMany`. For multiple replicas sharing model cache, consider EFS (see Step 11).

**Deploy all components:**

```bash
cd k8s

# Create storage
kubectl apply -f storage.yaml
kubectl get pvc model-storage

# Create config maps
kubectl apply -f config.yaml

# Deploy inference servers
kubectl apply -f inference-service.yaml
kubectl apply -f inference-headless-service.yaml
kubectl apply -f inference-deployment.yaml

# Deploy trainer
kubectl apply -f trainer-service.yaml
kubectl apply -f trainer-deployment.yaml

# Deploy UI
kubectl apply -f ui-deployment.yaml
kubectl apply -f ui-service.yaml
```

**Or use the deployment script:**

```bash
./deploy.sh
```

**Verify deployment:**

```bash
kubectl get pods -o wide
kubectl get services
kubectl logs -l app=inference-server --tail=50
```

### Step 11: Configure Shared Storage (Optional - for ReadWriteMany)

If you need multiple replicas to share the same model cache, use EFS:

**Create EFS file system:**

```bash
# Create EFS
aws efs create-file-system --creation-token ai-infra-efs --region $REGION

# Get file system ID
EFS_ID=$(aws efs describe-file-systems --creation-token ai-infra-efs --query 'FileSystems[0].FileSystemId' --output text --region $REGION)

# Get VPC and subnet IDs
VPC_ID=$(aws eks describe-cluster --name ai-infra-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text --region $REGION)
SUBNET_IDS=$(aws eks describe-cluster --name ai-infra-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text --region $REGION)

# Create mount targets for each subnet
for SUBNET in $SUBNET_IDS; do
  aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id $SUBNET \
    --security-groups $(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=*eks-cluster-sg*" --query 'SecurityGroups[0].GroupId' --output text --region $REGION) \
    --region $REGION
done
```

**Install EFS CSI driver:**

```bash
kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.7"
```

**Create EFS StorageClass and PVC:**

Create `k8s/efs-storage.yaml`:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: <EFS_ID>
  directoryPerms: "0755"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 100Gi
```

Apply it:
```bash
kubectl apply -f k8s/efs-storage.yaml
```

### Step 12: Access Services

**Option 1: Port Forwarding (for testing)**

```bash
# UI Service
kubectl port-forward svc/ui-service 8080:80
# Open http://localhost:8080 in browser

# Inference Service
kubectl port-forward svc/inference-service 8000:8000
```

**Option 2: Load Balancer (for production)**

The `ui-service.yaml` is already configured as `type: LoadBalancer`. Get the external URL:

```bash
kubectl get svc ui-service
# Wait for EXTERNAL-IP to be assigned, then access http://<EXTERNAL-IP>:80
```

**Option 3: Ingress (recommended for production)**

Install AWS Load Balancer Controller and configure Ingress (see original deployment plan for details).

### Step 3: Create EKS Cluster

The project includes an `eks-cluster.yaml` configuration file. Review and customize it:

```bash
# Review cluster configuration
cat eks-cluster.yaml
```

The configuration includes:
- **Cluster name**: `ai-infra-cluster`
- **Region**: `us-east-1` (customize as needed)
- **Kubernetes version**: `1.29`
- **Node groups**:
  - **CPU nodes**: `t3.large` instances (2 desired, 1-3 range)
  - **GPU nodes**: `g4dn.xlarge` instances with NVIDIA T4 GPUs (1 desired, 1-2 range)

**Create the cluster:**

```bash
eksctl create cluster -f eks-cluster.yaml
```

This will take approximately 15-20 minutes. The command will:
- Create VPC, subnets, and security groups
- Create EKS control plane
- Create managed node groups
- Configure kubectl context

**Verify cluster creation:**

```bash
kubectl get nodes
kubectl get nodes -l role=gpu  # Check GPU nodes
```

### Step 4: Install NVIDIA Device Plugin

GPU nodes require the NVIDIA device plugin for Kubernetes:

```bash
# Apply NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml

# Verify installation
kubectl get daemonset -n kube-system nvidia-device-plugin-daemonset
```

### Step 5: Create ECR Repositories

Create ECR repositories for Docker images:

```bash
# Set variables
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create repositories
aws ecr create-repository --repository-name ai-infra-inference --region $AWS_REGION
aws ecr create-repository --repository-name ai-infra-trainer --region $AWS_REGION
aws ecr create-repository --repository-name ai-infra-ui --region $AWS_REGION

# Get login token
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

### Step 6: Build and Push Docker Images

**Update Dockerfiles with ECR base images if needed**, then build and push:

```bash
# Set variables
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_BASE

# Build and push inference server
docker build -f docker/inference-server.Dockerfile -t $ECR_BASE/ai-infra-inference:latest .
docker push $ECR_BASE/ai-infra-inference:latest

# Build and push trainer server
docker build -f docker/trainer-server.Dockerfile -t $ECR_BASE/ai-infra-trainer:latest .
docker push $ECR_BASE/ai-infra-trainer:latest

# Build and push UI server
docker build -f docker/ui-server.Dockerfile -t $ECR_BASE/ai-infra-ui:latest .
docker push $ECR_BASE/ai-infra-ui:latest
```

### Step 7: Update Kubernetes Manifests

Update the Kubernetes deployment files to use ECR images:

**Update `k8s/inference-deployment.yaml`:**

Replace the image line (around line 20):
```yaml
image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-infra-inference:latest
```

With your ECR URL:
```yaml
image: <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/ai-infra-inference:latest
```

**Update `k8s/trainer-deployment.yaml` and `k8s/ui-deployment.yaml`** similarly.

**Update storage class:**

Check if your EKS cluster has a default storage class:
```bash
kubectl get storageclass
```

If using EBS CSI driver (default in EKS), update `k8s/storage.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage
spec:
  accessModes:
    - ReadWriteMany  # Note: EBS doesn't support ReadWriteMany
  # For EBS, use ReadWriteOnce and consider alternatives:
  # - Use EFS for ReadWriteMany
  # - Use ReadWriteOnce and single replica
  # - Use NFS or other shared storage solution
```

**For ReadWriteMany support, use EFS:**

1. **Create EFS file system:**
```bash
# Create EFS
aws efs create-file-system --creation-token ai-infra-efs --region $AWS_REGION

# Get file system ID
EFS_ID=$(aws efs describe-file-systems --creation-token ai-infra-efs --query 'FileSystems[0].FileSystemId' --output text --region $AWS_REGION)

# Get VPC and subnet IDs
VPC_ID=$(aws eks describe-cluster --name ai-infra-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text --region $AWS_REGION)
SUBNET_IDS=$(aws eks describe-cluster --name ai-infra-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text --region $AWS_REGION)

# Create mount targets
for SUBNET in $SUBNET_IDS; do
  aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id $SUBNET \
    --security-groups $(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=*eks-cluster-sg*" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION) \
    --region $AWS_REGION
done
```

2. **Install EFS CSI driver:**
```bash
kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.7"
```

3. **Create EFS StorageClass and PVC:**
Create `k8s/efs-storage.yaml`:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: <EFS_ID>
  directoryPerms: "0755"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 100Gi
```

### Step 8: Configure Node Affinity for GPU Pods

Ensure inference pods are scheduled on GPU nodes. Update `k8s/inference-deployment.yaml`:

```yaml
spec:
  template:
    spec:
      nodeSelector:
        role: gpu
      containers:
      - name: inference-server
        # ... rest of config
```

### Step 9: Deploy to EKS

```bash
# Ensure kubectl context is set
kubectl config current-context  # Should show ai-infra-cluster

# Deploy
cd k8s
./deploy.sh

# Or deploy to specific namespace
kubectl create namespace ai-infra
./deploy.sh ai-infra
```

### Step 10: Verify Deployment

```bash
# Check pods
kubectl get pods -o wide

# Check services
kubectl get services

# Check PVC
kubectl get pvc

# Check GPU allocation
kubectl describe nodes -l role=gpu | grep nvidia.com/gpu

# View logs
kubectl logs -l app=inference-server --tail=50
kubectl logs -l app=trainer-server --tail=50
kubectl logs -l app=ui-server --tail=50
```

### Step 11: Access Services

**Option 1: Port Forwarding (for testing)**

```bash
# UI Service
kubectl port-forward svc/ui-service 8080:80

# Inference Service
kubectl port-forward svc/inference-service 8000:8000
```

**Option 2: Load Balancer (for production)**

Update service types to `LoadBalancer`:

```yaml
# k8s/ui-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ui-service
spec:
  type: LoadBalancer  # Change from ClusterIP
  ports:
  - port: 80
    targetPort: 8080
```

Then get the external URL:
```bash
kubectl get svc ui-service
# Use EXTERNAL-IP or use AWS Load Balancer DNS name
```

**Option 3: Ingress (recommended for production)**

Install AWS Load Balancer Controller:

```bash
# Install controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ai-infra-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

Create Ingress resource (create `k8s/ingress.yaml`):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-infra-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: ai-infra.example.com  # Replace with your domain
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ui-service
            port:
              number: 80
      - path: /api/inference
        pathType: Prefix
        backend:
          service:
            name: inference-service
            port:
              number: 8000
```

### Step 13: Troubleshooting Common Issues

**Issue: Pods stuck in Pending**

```bash
kubectl describe pod <pod-name>
# Check for:
# - Resource constraints (CPU/memory/GPU)
# - Node selectors (inference pods need role=gpu)
# - Taints and tolerations
# - PVC binding issues
```

**Issue: GPU not available**

```bash
# Check device plugin
kubectl get daemonset -n kube-system nvidia-device-plugin-daemonset

# Check node labels
kubectl get nodes -l role=gpu --show-labels

# Check GPU resources
kubectl describe node <gpu-node> | grep nvidia.com/gpu

# Verify GPU nodes are running
kubectl get nodes -l role=gpu
```

**Issue: Image pull errors**

```bash
# Verify ECR login
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

# Check image exists in ECR
aws ecr describe-images --repository-name ai-infra-inference --region $REGION

# Check pod events
kubectl describe pod <pod-name> | grep -A 10 Events
```

**Issue: GPU nodegroup creation fails with VcpuLimitExceeded**

This means your AWS account has 0 vCPU quota for GPU instances:

1. Go to **Service Quotas** → **EC2** → Search "Running On-Demand G and VT instances"
2. Click **Request quota increase**
3. Request at least 16 vCPU (for g4dn.xlarge: 4 vCPU each)
4. Wait for approval (usually minutes to hours)
5. After approval, delete failed nodegroup and recreate:

```bash
eksctl delete nodegroup --cluster ai-infra-cluster --name gpu-nodes --region us-east-1 --approve
eksctl create nodegroup --config-file eks-cluster.yaml --include gpu-nodes
```

**Issue: CloudFormation stack already exists**

If you see "Stack already exists" error:

```bash
# Delete the cluster completely
eksctl delete cluster --name ai-infra-cluster --region us-east-1 --wait

# Or manually delete stacks in CloudFormation console:
# - eksctl-ai-infra-cluster-cluster
# - eksctl-ai-infra-cluster-nodegroup-cpu-nodes
# - eksctl-ai-infra-cluster-nodegroup-gpu-nodes
```

**Issue: PVC stuck in Pending**

```bash
# Check storage class
kubectl get storageclass

# Check PVC details
kubectl describe pvc model-storage

# If using EBS, ensure storageClassName is set to gp3 or gp2
# Update k8s/storage.yaml if needed
```

**Issue: eksctl installation fails in WSL**

If you get "No URLs found" or tar errors:

```bash
# Use the recommended installation method
ARCH=amd64
PLATFORM=$(uname -s)_$ARCH
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"
tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp
sudo install -m 0755 /tmp/eksctl /usr/local/bin
eksctl version
```

**Issue: Docker push fails with "no basic auth credentials"**

```bash
# Ensure you're logged in (not using sudo)
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

# If using sudo, either:
# 1. Add user to docker group: sudo usermod -aG docker $USER (then restart terminal)
# 2. Or login with sudo: aws ecr get-login-password --region $REGION | sudo docker login --username AWS --password-stdin $REGISTRY
```

### Step 14: Monitoring and Scaling

**Enable CloudWatch logging:**

```bash
aws eks update-cluster-config \
  --name ai-infra-cluster \
  --logging '{"enable":["api","audit","authenticator","controllerManager","scheduler"]}' \
  --region us-east-1
```

**View logs:**

```bash
# Log groups in CloudWatch:
# /aws/eks/ai-infra-cluster/cluster
# /aws/containerinsights/ai-infra-cluster/application
```

**Horizontal Pod Autoscaling:**

Create `k8s/hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-server
  minReplicas: 2
  maxReplicas: 10
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
```

Apply: `kubectl apply -f k8s/hpa.yaml`

**Cluster Autoscaling:**

Already configured in `eks-cluster.yaml`:
- CPU nodes: 1-3 instances (auto-scales based on demand)
- GPU nodes: 1-2 instances

### Step 15: Cost Optimization

**Monthly cost estimate (us-east-1):**
- EKS Control Plane: ~$73/month
- 2x t3.large (CPU nodes): ~$60/month
- 1x g4dn.xlarge (GPU node): ~$200/month
- EBS storage (100GB): ~$10/month
- EFS (if used, 100GB): ~$30/month
- **Total: ~$373/month** (excluding data transfer)

**Cost optimization strategies:**

1. **Use Spot Instances for GPU nodes:**
   Update `eks-cluster.yaml`:
   ```yaml
   managedNodeGroups:
     - name: gpu-nodes
       instanceType: g4dn.xlarge
       spot: true  # 60-70% cost savings
       desiredCapacity: 1
   ```

2. **Scale down during non-business hours:**
   ```bash
   kubectl scale deployment inference-server --replicas=0
   # Scale GPU nodegroup to 0
   eksctl scale nodegroup --cluster ai-infra-cluster --name gpu-nodes --nodes 0
   ```

3. **Use smaller instance types for development:**
   - Use `t3.medium` for CPU nodes
   - Use `g4dn.xlarge` only when needed

4. **Delete cluster when not in use:**
   ```bash
   eksctl delete cluster --name ai-infra-cluster --region us-east-1 --wait
   ```

### Step 16: Cleanup

**Delete the entire cluster:**

```bash
eksctl delete cluster --name ai-infra-cluster --region us-east-1 --wait
```

This will delete:
- EKS control plane
- All node groups
- VPC and networking resources (if created by eksctl)
- CloudFormation stacks

**Delete ECR repositories (optional):**

```bash
aws ecr delete-repository --repository-name ai-infra-inference --force --region us-east-1
aws ecr delete-repository --repository-name ai-infra-trainer --force --region us-east-1
aws ecr delete-repository --repository-name ai-infra-ui --force --region us-east-1
```

**Delete EFS (if created):**

```bash
aws efs delete-file-system --file-system-id $EFS_ID --region us-east-1
```

**Note:** Always verify resources are deleted in AWS Console to avoid unexpected charges.

---

