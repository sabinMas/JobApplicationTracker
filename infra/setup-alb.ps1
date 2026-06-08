# Setup Application Load Balancer for ECS Fargate API service
# This makes the API publicly accessible

param(
    [string]$ClusterName = "jobtracker-cluster",
    [string]$ServiceName = "api-service",
    [string]$ALBName = "jobtracker-api-alb",
    [int]$ContainerPort = 8000,
    [string]$Region = "us-east-1"
)

Write-Host "Setting up Application Load Balancer for $ServiceName"

# Get VPC ID from ECS cluster
$vpcId = aws ec2 describe-vpcs --region $Region --query 'Vpcs[0].VpcId' --output text
Write-Host "VPC ID: $vpcId"

# Get subnets
$subnets = aws ec2 describe-subnets --region $Region --filters "Name=vpc-id,Values=$vpcId" --query 'Subnets[*].SubnetId' --output text
Write-Host "Subnets: $subnets"

# Create security group for ALB
Write-Host "`nCreating security group for ALB..."
$sgName = "jobtracker-alb-sg"
$sgId = aws ec2 describe-security-groups --region $Region --filters "Name=group-name,Values=$sgName" --query 'SecurityGroups[0].GroupId' --output text 2>$null

if ($sgId -eq "None" -or [string]::IsNullOrEmpty($sgId)) {
    $sgId = aws ec2 create-security-group --group-name $sgName --description "ALB security group for JobApplicationTracker" --vpc-id $vpcId --region $Region --query 'GroupId' --output text
    Write-Host "Created security group: $sgId"
    
    # Allow HTTP
    aws ec2 authorize-security-group-ingress --group-id $sgId --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $Region 2>$null
    # Allow HTTPS
    aws ec2 authorize-security-group-ingress --group-id $sgId --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $Region 2>$null
} else {
    Write-Host "Using existing security group: $sgId"
}

# Create ALB
Write-Host "`nCreating Application Load Balancer..."
$albArn = aws elbv2 describe-load-balancers --region $Region --names $ALBName --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>$null

if ($albArn -eq "None" -or [string]::IsNullOrEmpty($albArn)) {
    $subnetArray = $subnets -split '\s+' | Select-Object -First 2
    $albResult = aws elbv2 create-load-balancer `
        --name $ALBName `
        --subnets $subnetArray `
        --security-groups $sgId `
        --scheme internet-facing `
        --type application `
        --region $Region `
        --output json | ConvertFrom-Json
    
    $albArn = $albResult.LoadBalancers[0].LoadBalancerArn
    $albDns = $albResult.LoadBalancers[0].DNSName
    Write-Host "Created ALB: $albArn"
    Write-Host "ALB DNS: $albDns"
} else {
    Write-Host "Using existing ALB: $albArn"
    $albDns = aws elbv2 describe-load-balancers --region $Region --load-balancer-arns $albArn --query 'LoadBalancers[0].DNSName' --output text
    Write-Host "ALB DNS: $albDns"
}

# Create target group
Write-Host "`nCreating target group..."
$tgName = "jobtracker-api-tg"
$tgArn = aws elbv2 describe-target-groups --region $Region --names $tgName --query 'TargetGroups[0].TargetGroupArn' --output text 2>$null

if ($tgArn -eq "None" -or [string]::IsNullOrEmpty($tgArn)) {
    $tgResult = aws elbv2 create-target-group `
        --name $tgName `
        --protocol HTTP `
        --port $ContainerPort `
        --vpc-id $vpcId `
        --target-type ip `
        --health-check-enabled `
        --health-check-protocol HTTP `
        --health-check-path /health `
        --health-check-interval-seconds 30 `
        --health-check-timeout-seconds 5 `
        --healthy-threshold-count 2 `
        --unhealthy-threshold-count 3 `
        --matcher HttpCode=200 `
        --region $Region `
        --output json | ConvertFrom-Json
    
    $tgArn = $tgResult.TargetGroups[0].TargetGroupArn
    Write-Host "Created target group: $tgArn"
} else {
    Write-Host "Using existing target group: $tgArn"
}

# Create listener
Write-Host "`nCreating ALB listener..."
$listenerArn = aws elbv2 describe-listeners --region $Region --load-balancer-arn $albArn --query 'Listeners[0].ListenerArn' --output text 2>$null

if ($listenerArn -eq "None" -or [string]::IsNullOrEmpty($listenerArn)) {
    aws elbv2 create-listener `
        --load-balancer-arn $albArn `
        --protocol HTTP `
        --port 80 `
        --default-actions Type=forward,TargetGroupArn=$tgArn `
        --region $Region > $null
    Write-Host "Created listener on port 80"
} else {
    Write-Host "Listener already exists"
}

# Update ECS service to use ALB
Write-Host "`nUpdating ECS service to use ALB target group..."
aws ecs update-service `
    --cluster $ClusterName `
    --service $ServiceName `
    --load-balancers targetGroupArn=$tgArn,containerName=api,containerPort=$ContainerPort `
    --region $Region > $null

Write-Host "`n✅ ALB Setup Complete!"
Write-Host "API will be available at: http://$albDns"
Write-Host ""
Write-Host "Note: It may take 1-2 minutes for the load balancer to pass health checks"
Write-Host "and become fully operational."
