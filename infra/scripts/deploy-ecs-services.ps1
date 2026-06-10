# Deploy ECS services (API + Workers)
# Creates task definitions and launches services

param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "jobtracker-cluster",
    [string]$AwsAccountId = "245091941294",
    [string]$VpcSubnet = "",  # Will be auto-detected if blank
    [string]$SecurityGroup = ""  # Will be auto-detected if blank
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Deploy ECS Services ===" -ForegroundColor Green
Write-Host "Region: $Region`nCluster: $ClusterName`n" -ForegroundColor Cyan

# Configuration
$ApiImageUri = "$AwsAccountId.dkr.ecr.$Region.amazonaws.com/jobtracker-api:latest"
$WorkerImageUri = "$AwsAccountId.dkr.ecr.$Region.amazonaws.com/jobtracker-worker:latest"
$SqsQueueName = "jobtracker-scraping-tasks"
$S3Bucket = "jobtracker-documents-245091941294"
$DbEndpoint = "jobtracker-db.cmnwwqsqogwv.us-east-1.rds.amazonaws.com"
$DbName = "jobtracker"

function Get-VpcDefaults {
    Write-Host "Getting VPC defaults..." -ForegroundColor Gray

    if ([string]::IsNullOrEmpty($script:VpcSubnet)) {
        $ec2 = aws ec2 describe-subnets --filters "Name=availability-zone,Values=${Region}a" --region $Region | ConvertFrom-Json
        if ($ec2.Subnets.Count -gt 0) {
            $script:VpcSubnet = $ec2.Subnets[0].SubnetId
            Write-Host "Auto-detected subnet: $($script:VpcSubnet)" -ForegroundColor Gray
        } else {
            # Fallback: get default VPC's first subnet
            $vpcs = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region $Region | ConvertFrom-Json
            if ($vpcs.Vpcs.Count -gt 0) {
                $vpcId = $vpcs.Vpcs[0].VpcId
                $subnets = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpcId" --region $Region | ConvertFrom-Json
                $script:VpcSubnet = $subnets.Subnets[0].SubnetId
            }
        }
    }

    if ([string]::IsNullOrEmpty($script:SecurityGroup)) {
        $sgs = aws ec2 describe-security-groups --filters "Name=group-name,Values=default" --region $Region | ConvertFrom-Json
        if ($sgs.SecurityGroups.Count -gt 0) {
            $script:SecurityGroup = $sgs.SecurityGroups[0].GroupId
            Write-Host "Auto-detected security group: $($script:SecurityGroup)" -ForegroundColor Gray
        }
    }
}

function Register-ApiTaskDefinition {
    Write-Host "`n[1] Registering API task definition..." -ForegroundColor Yellow

    $taskDefFile = "$env:TEMP\jobtracker-api-taskdef.json"
    $taskDefObj = @{
        family = "jobtracker-api-task"
        networkMode = "awsvpc"
        requiresCompatibilities = @("FARGATE")
        cpu = "512"
        memory = "1024"
        executionRoleArn = "arn:aws:iam::${AwsAccountId}:role/ecsTaskExecutionRole"
        taskRoleArn = "arn:aws:iam::${AwsAccountId}:role/ecsTaskRole"
        containerDefinitions = @(
            @{
                name = "api"
                image = $ApiImageUri
                essential = $true
                portMappings = @(
                    @{ containerPort = 8000; hostPort = 8000; protocol = "tcp" }
                )
                environment = @(
                    @{ name = "S3_BUCKET"; value = $S3Bucket }
                    @{ name = "ALLOWED_ORIGINS"; value = "https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app,http://localhost:5173" }
                    @{ name = "ENVIRONMENT"; value = "production" }
                    @{ name = "LOG_LEVEL"; value = "INFO" }
                )
                secrets = @(
                    @{ name = "CEREBRAS_API_KEY"; valueFrom = "arn:aws:secretsmanager:${Region}:${AwsAccountId}:secret:cerebras-api-key-cvPIUr" }
                    @{ name = "DATABASE_URL"; valueFrom = "arn:aws:secretsmanager:${Region}:${AwsAccountId}:secret:jobtracker-db-url-beawCh" }
                )
                logConfiguration = @{
                    logDriver = "awslogs"
                    options = @{
                        "awslogs-group" = "/ecs/jobtracker-api"
                        "awslogs-region" = $Region
                        "awslogs-stream-prefix" = "ecs"
                    }
                }
                healthCheck = @{
                    command = @("CMD-SHELL", "curl -f http://localhost:8000/health || exit 1")
                    interval = 30
                    timeout = 5
                    retries = 3
                    startPeriod = 60
                }
            }
        )
    }
    $taskDefObj | ConvertTo-Json -Depth 20 | Out-File -FilePath $taskDefFile -Encoding ascii

    # Create CloudWatch log group
    $ErrorActionPreference = "Continue"
    aws logs create-log-group --log-group-name "/ecs/jobtracker-api" --region $Region 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"

    # Register task definition
    aws ecs register-task-definition --cli-input-json "file://$taskDefFile" --region $Region | Out-Null

    Write-Host "API task definition registered" -ForegroundColor Green
}

function Register-WorkerTaskDefinition {
    Write-Host "`n[2] Registering Worker task definition..." -ForegroundColor Yellow

    # Get SQS queue URL
    $queueResponse = aws sqs get-queue-url --queue-name $SqsQueueName --region $Region | ConvertFrom-Json
    $queueUrl = $queueResponse.QueueUrl

    $taskDefFile = "$env:TEMP\jobtracker-worker-taskdef.json"
    $taskDefObj = @{
        family = "jobtracker-worker-task"
        networkMode = "awsvpc"
        requiresCompatibilities = @("FARGATE")
        cpu = "1024"
        memory = "2048"
        executionRoleArn = "arn:aws:iam::${AwsAccountId}:role/ecsTaskExecutionRole"
        taskRoleArn = "arn:aws:iam::${AwsAccountId}:role/ecsTaskRole"
        containerDefinitions = @(
            @{
                name = "worker"
                image = $WorkerImageUri
                essential = $true
                environment = @(
                    @{ name = "S3_BUCKET"; value = $S3Bucket }
                    @{ name = "SQS_QUEUE_URL"; value = $queueUrl }
                    @{ name = "ENVIRONMENT"; value = "production" }
                    @{ name = "LOG_LEVEL"; value = "INFO" }
                    @{ name = "AWS_DEFAULT_REGION"; value = $Region }
                )
                secrets = @(
                    @{ name = "CEREBRAS_API_KEY"; valueFrom = "arn:aws:secretsmanager:${Region}:${AwsAccountId}:secret:cerebras-api-key-cvPIUr" }
                    @{ name = "DATABASE_URL"; valueFrom = "arn:aws:secretsmanager:${Region}:${AwsAccountId}:secret:jobtracker-db-url-beawCh" }
                )
                logConfiguration = @{
                    logDriver = "awslogs"
                    options = @{
                        "awslogs-group" = "/ecs/jobtracker-worker"
                        "awslogs-region" = $Region
                        "awslogs-stream-prefix" = "ecs"
                    }
                }
            }
        )
    }
    $taskDefObj | ConvertTo-Json -Depth 20 | Out-File -FilePath $taskDefFile -Encoding ascii

    # Create CloudWatch log group
    $ErrorActionPreference = "Continue"
    aws logs create-log-group --log-group-name "/ecs/jobtracker-worker" --region $Region 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"

    # Register task definition
    aws ecs register-task-definition --cli-input-json "file://$taskDefFile" --region $Region | Out-Null

    Write-Host "Worker task definition registered" -ForegroundColor Green
}

function Create-ApiService {
    Write-Host "`n[3] Creating API service..." -ForegroundColor Yellow

    $ErrorActionPreference = "Continue"
    $serviceExists = aws ecs describe-services --cluster $ClusterName --services "api-service" --region $Region 2>&1 | ConvertFrom-Json
    $ErrorActionPreference = "Stop"

    if ($serviceExists.services.Count -gt 0 -and $serviceExists.services[0].status -ne "INACTIVE") {
        Write-Host "API service exists, updating..." -ForegroundColor Gray
        aws ecs update-service `
            --cluster $ClusterName `
            --service "api-service" `
            --task-definition "jobtracker-api-task:1" `
            --force-new-deployment `
            --region $Region | Out-Null
    } else {
        Write-Host "Creating API service..." -ForegroundColor Gray
        aws ecs create-service `
            --cluster $ClusterName `
            --service-name "api-service" `
            --task-definition "jobtracker-api-task:1" `
            --desired-count 1 `
            --launch-type FARGATE `
            --network-configuration "awsvpcConfiguration={subnets=[$($script:VpcSubnet)],securityGroups=[$($script:SecurityGroup)],assignPublicIp=ENABLED}" `
            --region $Region | Out-Null
    }

    Write-Host "API service ready" -ForegroundColor Green
}

function Create-WorkerService {
    Write-Host "`n[4] Creating Worker service..." -ForegroundColor Yellow

    $ErrorActionPreference = "Continue"
    $serviceExists = aws ecs describe-services --cluster $ClusterName --services "worker-service" --region $Region 2>&1 | ConvertFrom-Json
    $ErrorActionPreference = "Stop"

    if ($serviceExists.services.Count -gt 0 -and $serviceExists.services[0].status -ne "INACTIVE") {
        Write-Host "Worker service exists, updating..." -ForegroundColor Gray
        aws ecs update-service `
            --cluster $ClusterName `
            --service "worker-service" `
            --task-definition "jobtracker-worker-task:1" `
            --desired-count 0 `
            --region $Region | Out-Null
    } else {
        Write-Host "Creating Worker service (initially 0 tasks, will auto-scale)..." -ForegroundColor Gray
        aws ecs create-service `
            --cluster $ClusterName `
            --service-name "worker-service" `
            --task-definition "jobtracker-worker-task:1" `
            --desired-count 0 `
            --launch-type FARGATE `
            --network-configuration "awsvpcConfiguration={subnets=[$($script:VpcSubnet)],securityGroups=[$($script:SecurityGroup)],assignPublicIp=ENABLED}" `
            --region $Region | Out-Null
    }

    Write-Host "Worker service ready" -ForegroundColor Green
}

function Create-TaskRole {
    Write-Host "`n[0] Ensuring task role exists..." -ForegroundColor Yellow

    $roleName = "ecsTaskRole"
    $ErrorActionPreference = "Continue"
    $role = aws iam get-role --role-name $roleName 2>&1
    $ErrorActionPreference = "Stop"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Task role exists" -ForegroundColor Gray
        return
    }

    Write-Host "Creating task role..." -ForegroundColor Gray

    $trustPolicyFile = "$env:TEMP\ecs-task-trust.json"
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
        --assume-role-policy-document "file://$trustPolicyFile" | Out-Null

    # Add inline policy for SQS, S3, Secrets Manager access
    $inlinePolicyFile = "$env:TEMP\ecs-task-runtime-policy.json"
    @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes","sqs:SendMessage")
                Resource = "arn:aws:sqs:${Region}:${AwsAccountId}:jobtracker-scraping-tasks"
            },
            @{
                Effect = "Allow"
                Action = @("s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket")
                Resource = @("arn:aws:s3:::${S3Bucket}","arn:aws:s3:::${S3Bucket}/*")
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
        --policy-name "ecs-task-runtime-policy" `
        --policy-document "file://$inlinePolicyFile" | Out-Null

    Write-Host "Task role created" -ForegroundColor Green
}

# Main execution
Get-VpcDefaults
Create-TaskRole
Register-ApiTaskDefinition
Register-WorkerTaskDefinition
Create-ApiService
Create-WorkerService

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host "API Service: http://${region}.compute.amazonaws.com:8000" -ForegroundColor Cyan
Write-Host "Monitor: aws ecs describe-services --cluster $ClusterName --services api-service --region $Region" -ForegroundColor Cyan
Write-Host "`nNext: Update Vercel environment with the API endpoint`n" -ForegroundColor Yellow
