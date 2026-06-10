# Configure ECS worker service auto-scaling based on SQS queue depth

param(
    [string]$ClusterName = "jobtracker-cluster",
    [string]$ServiceName = "worker-service",
    [string]$QueueName = "jobtracker-scraper-runs",
    [int]$MinTasks = 0,
    [int]$MaxTasks = 5,
    [double]$TargetQueueDepth = 10,
    [string]$Region = "us-east-1"
)

Write-Host "Configuring auto-scaling for $ServiceName"
Write-Host "Min tasks: $MinTasks, Max tasks: $MaxTasks"
Write-Host "Target queue depth: $TargetQueueDepth messages per task"

# Register scalable target
Write-Host "`nRegistering scalable target..."
$serviceArn = "arn:aws:ecs:$Region:245091941294:service/$ClusterName/$ServiceName"

aws application-autoscaling register-scalable-target `
    --service-namespace ecs `
    --resource-id "service/$ClusterName/$ServiceName" `
    --scalable-dimension ecs:service:DesiredCount `
    --min-capacity $MinTasks `
    --max-capacity $MaxTasks `
    --region $Region 2>$null

Write-Host "Registered scalable target"

# Get queue ARN
$queueUrl = aws sqs get-queue-url --queue-name $QueueName --region $Region --query 'QueueUrl' --output text
Write-Host "Queue URL: $queueUrl"

# Create scaling policy
Write-Host "`nCreating scaling policy..."

$policyJson = @{
    AdjustmentType = "ChangeInCapacity"
    MetricAggregationType = "Average"
    StepAdjustments = @(
        @{
            MetricIntervalLowerBound = 0
            MetricIntervalUpperBound = $TargetQueueDepth
            ScalingAdjustment = 0
        },
        @{
            MetricIntervalLowerBound = $TargetQueueDepth
            MetricIntervalUpperBound = $TargetQueueDepth * 2
            ScalingAdjustment = 1
        },
        @{
            MetricIntervalLowerBound = $TargetQueueDepth * 2
            ScalingAdjustment = 2
        }
    )
} | ConvertTo-Json

aws application-autoscaling put-scaling-policy `
    --policy-name "jobtracker-worker-scaling" `
    --service-namespace ecs `
    --resource-id "service/$ClusterName/$ServiceName" `
    --scalable-dimension ecs:service:DesiredCount `
    --policy-type StepScaling `
    --step-scaling-policy-configuration "$policyJson" `
    --region $Region 2>$null

Write-Host "Created scaling policy"

# Create CloudWatch alarm for scaling
Write-Host "`nCreating CloudWatch alarm..."

aws cloudwatch put-metric-alarm `
    --alarm-name "jobtracker-worker-queue-depth" `
    --alarm-description "Scale workers based on SQS queue depth" `
    --metric-name ApproximateNumberOfMessagesVisible `
    --namespace AWS/SQS `
    --statistic Average `
    --period 60 `
    --evaluation-periods 2 `
    --threshold $TargetQueueDepth `
    --comparison-operator GreaterThanThreshold `
    --dimensions Name=QueueName,Value=$QueueName `
    --alarm-actions "arn:aws:autoscaling:$Region:245091941294:policy/jobtracker-worker-scaling:policyName/jobtracker-worker-scaling" `
    --region $Region 2>$null

Write-Host "Created CloudWatch alarm"

Write-Host "`n✅ Auto-scaling configured!"
Write-Host "Worker service will scale from $MinTasks to $MaxTasks tasks"
Write-Host "based on SQS queue depth (target: $TargetQueueDepth messages per task)"
