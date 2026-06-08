# Setup ECS Fargate Infrastructure
# Creates ECR repos, builds Docker images, deploys to ECS

param(
    [string]$Action = "full",  # full, build-only, deploy-only
    [string]$Region = "us-east-1",
    [string]$ClusterName = "jobtracker-cluster",
    [string]$AwsAccountId = "245091941294"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== ECS Fargate Setup ===" -ForegroundColor Green
Write-Host "Action: $Action`nRegion: $Region`nCluster: $ClusterName`n" -ForegroundColor Cyan

# Configuration
$ApiImageName = "jobtracker-api"
$WorkerImageName = "jobtracker-worker"
$EcrUri = "$AwsAccountId.dkr.ecr.$Region.amazonaws.com"
$SqsQueueName = "jobtracker-scraping-tasks"
$S3Bucket = "jobtracker-documents-245091941294"

function Get-EcsTaskExecutionRoleArn {
    Write-Host "`n[1] Checking ECS task execution role..." -ForegroundColor Yellow

    $roleName = "ecsTaskExecutionRole"
    $ErrorActionPreference = "Continue"
    $role = aws iam get-role --role-name $roleName --region $Region 2>&1
    $ErrorActionPreference = "Stop"

    if ($LASTEXITCODE -eq 0) {
        $arn = ($role | ConvertFrom-Json).Role.Arn
        Write-Host "Found role: $arn" -ForegroundColor Green
        return $arn
    }

    Write-Host "Creating $roleName..." -ForegroundColor Yellow

    $trustPolicyFile = "$env:TEMP\ecs-trust-policy.json"
    @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "ecs-tasks.amazonaws.com" }
                Action = "sts:AssumeRole"
            }
        )
    } | ConvertTo-Json -Depth 10 | Out-File -FilePath $trustPolicyFile -Encoding ascii

    aws iam create-role `
        --role-name $roleName `
        --assume-role-policy-document "file://$trustPolicyFile" `
        --region $Region | Out-Null

    aws iam attach-role-policy `
        --role-name $roleName `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" `
        --region $Region | Out-Null

    # Add permissions for ECR, CloudWatch, S3, RDS, SQS
    $inlinePolicyFile = "$env:TEMP\ecs-inline-policy.json"
    @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("ecr:GetAuthorizationToken","ecr:BatchGetImage","ecr:GetDownloadUrlForLayer","ecr:BatchCheckLayerAvailability")
                Resource = "*"
            },
            @{
                Effect = "Allow"
                Action = @("logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents")
                Resource = "arn:aws:logs:${Region}:${AwsAccountId}:log-group:/ecs/*"
            },
            @{
                Effect = "Allow"
                Action = @("s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket")
                Resource = @("arn:aws:s3:::${S3Bucket}","arn:aws:s3:::${S3Bucket}/*")
            },
            @{
                Effect = "Allow"
                Action = @("sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes","sqs:SendMessage")
                Resource = "arn:aws:sqs:${Region}:${AwsAccountId}:${SqsQueueName}"
            },
            @{
                Effect = "Allow"
                Action = @("secretsmanager:GetSecretValue")
                Resource = "arn:aws:secretsmanager:${Region}:${AwsAccountId}:secret:*"
            }
        )
    } | ConvertTo-Json -Depth 10 | Out-File -FilePath $inlinePolicyFile -Encoding ascii

    aws iam put-role-policy `
        --role-name $roleName `
        --policy-name "ecs-task-policy" `
        --policy-document "file://$inlinePolicyFile" `
        --region $Region | Out-Null

    Write-Host "Created role" -ForegroundColor Green

    # Wait for role to propagate
    Start-Sleep -Seconds 10

    $roleArn = "arn:aws:iam::$AwsAccountId:role/$roleName"
    return $roleArn
}

function Create-EcrRepositories {
    Write-Host "`n[2] Setting up ECR repositories..." -ForegroundColor Yellow

    foreach ($repo in @($ApiImageName, $WorkerImageName)) {
        Write-Host "Checking ECR repo: $repo" -ForegroundColor Gray

        $ErrorActionPreference = "Continue"
        $exists = aws ecr describe-repositories --repository-names $repo --region $Region 2>&1
        $ErrorActionPreference = "Stop"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Creating ECR repo: $repo" -ForegroundColor Gray
            aws ecr create-repository --repository-name $repo --region $Region | Out-Null
        } else {
            Write-Host "Repo exists: $repo" -ForegroundColor Gray
        }
    }

    Write-Host "ECR repositories ready" -ForegroundColor Green
}

function Build-And-PushImages {
    Write-Host "`n[3] Building Docker images..." -ForegroundColor Yellow

    # Login to ECR (use cmd pipe — PowerShell pipe breaks password-stdin)
    Write-Host "Logging into ECR..." -ForegroundColor Gray
    $loginCmd = "aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $EcrUri"
    cmd /c $loginCmd

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to login to ECR" -ForegroundColor Red
        return $false
    }

    # Build API image
    Write-Host "Building API image..." -ForegroundColor Gray
    docker build -f Dockerfile.api -t $ApiImageName .

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to build API image" -ForegroundColor Red
        return $false
    }

    # Build Worker image
    Write-Host "Building worker image..." -ForegroundColor Gray
    docker build -f Dockerfile.worker -t $WorkerImageName .

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to build worker image" -ForegroundColor Red
        return $false
    }

    # Tag and push API
    Write-Host "Pushing API image..." -ForegroundColor Gray
    $ApiUri = "$EcrUri/$ApiImageName"
    docker tag $ApiImageName "${ApiUri}:latest"
    docker push "${ApiUri}:latest"

    # Tag and push Worker
    Write-Host "Pushing worker image..." -ForegroundColor Gray
    $WorkerUri = "$EcrUri/$WorkerImageName"
    docker tag $WorkerImageName "${WorkerUri}:latest"
    docker push "${WorkerUri}:latest"

    Write-Host "Images pushed to ECR" -ForegroundColor Green
    return $true
}

function Create-EcsCluster {
    Write-Host "`n[4] Creating ECS cluster..." -ForegroundColor Yellow

    $exists = aws ecs describe-clusters --clusters $ClusterName --region $Region 2>&1 | ConvertFrom-Json

    if ($exists.clusters.Count -eq 0) {
        Write-Host "Creating cluster: $ClusterName" -ForegroundColor Gray
        aws ecs create-cluster --cluster-name $ClusterName --region $Region | Out-Null
    } else {
        Write-Host "Cluster exists" -ForegroundColor Gray
    }

    Write-Host "Cluster ready" -ForegroundColor Green
}

function Create-SqsQueue {
    Write-Host "`n[5] Creating SQS queue..." -ForegroundColor Yellow

    $ErrorActionPreference = "Continue"
    $response = aws sqs get-queue-url --queue-name $SqsQueueName --region $Region 2>&1
    $ErrorActionPreference = "Stop"

    if ($LASTEXITCODE -eq 0) {
        $queueUrl = ($response | ConvertFrom-Json).QueueUrl
        Write-Host "Queue exists: $queueUrl" -ForegroundColor Gray
        return $queueUrl
    }

    Write-Host "Creating SQS queue: $SqsQueueName" -ForegroundColor Gray
    $response = aws sqs create-queue `
        --queue-name $SqsQueueName `
        --attributes "VisibilityTimeout=300,MessageRetentionPeriod=1209600" `
        --region $Region

    $queueUrl = ($response | ConvertFrom-Json).QueueUrl
    Write-Host "Queue created: $queueUrl" -ForegroundColor Green
    return $queueUrl
}

# Main execution
if ($Action -in @("full", "build-only")) {
    Create-EcrRepositories
    Build-And-PushImages
}

if ($Action -in @("full", "deploy-only")) {
    $executionRoleArn = Get-EcsTaskExecutionRoleArn
    Create-EcsCluster
    $queueUrl = Create-SqsQueue

    Write-Host "`n[6] Cluster ready for service deployment" -ForegroundColor Green
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Run: .\infra\deploy-ecs-services.ps1" -ForegroundColor Gray
    Write-Host "2. Update environment variables in task definitions" -ForegroundColor Gray
    Write-Host "3. Monitor: aws ecs describe-services --cluster $ClusterName --services api-service" -ForegroundColor Gray
}

Write-Host "`nSetup complete!`n" -ForegroundColor Green
