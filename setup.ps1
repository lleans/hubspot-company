# Microsoft User Extraction Service - Multi-Environment Setup Script
# Usage: .\setup.ps1 [environment] [action]
# Environments: dev, prod, stage, test
# Actions: up, down, restart, logs, clean

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "prod", "stage", "test")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("up", "down", "restart", "logs", "clean", "build", "status")]
    [string]$Action = "up",
    
    [Parameter(Mandatory=$false)]
    [switch]$Build = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Detach = $false
)

# Color functions for output
function Write-Header {
    param([string]$Message)
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Command {
    param([string]$Message)
    Write-Host "[COMMAND] $Message" -ForegroundColor Magenta
}

function Write-Output {
    param([string]$Message)
    Write-Host "[OUTPUT] $Message" -ForegroundColor Gray
}

# Check if Docker is running
function Test-DockerRunning {
    try {
        $null = docker version 2>$null
        return $true
    }
    catch {
        return $false
    }
}

# Check if docker-compose is available
function Test-DockerCompose {
    try {
        $null = docker-compose version 2>$null
        return $true
    }
    catch {
        return $false
    }
}

# Get compose file path
function Get-ComposeFile {
    param([string]$EnvType)
    return "docker/docker-compose.$EnvType.yml"
}

# Execute command with real-time output
function Invoke-CommandWithOutput {
    param(
        [string]$Command,
        [string]$WorkingDirectory = (Get-Location)
    )
    
    Write-Command "Executing: $Command"
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    
    try {
        # Split command and arguments for better handling
        $parts = $Command.Split(' ', [StringSplitOptions]::RemoveEmptyEntries)
        $executable = $parts[0]
        $arguments = $parts[1..($parts.Length-1)] -join ' '
        
        # Create process start info
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $executable
        $psi.Arguments = $arguments
        $psi.WorkingDirectory = $WorkingDirectory
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $false  # Show window for Docker Compose
        $psi.RedirectStandardOutput = $false  # Don't redirect, let it show in console
        $psi.RedirectStandardError = $false   # Don't redirect, let it show in console
        
        # For Docker Compose, we want to see all the native output
        if ($Command -like "*docker-compose*") {
            Write-Info "Running Docker Compose command - you'll see live output below:"
            Write-Host ""
            
            # Use Invoke-Expression to run in current console
            $originalLocation = Get-Location
            Set-Location $WorkingDirectory
            
            # Execute the command directly in the console
            Invoke-Expression $Command
            $exitCode = $LASTEXITCODE
            
            Set-Location $originalLocation
        }
        else {
            # For other commands, use process method
            $process = New-Object System.Diagnostics.Process
            $process.StartInfo = $psi
            
            $process.Start() | Out-Null
            $process.WaitForExit()
            $exitCode = $process.ExitCode
        }
        
        Write-Host ""
        Write-Host "----------------------------------------" -ForegroundColor DarkGray
        
        if ($exitCode -eq 0) {
            Write-Success "Command completed successfully (Exit Code: $exitCode)"
        } else {
            Write-Error "Command failed with exit code: $exitCode"
        }
        
        return $exitCode
    }
    catch {
        Write-Error "Failed to execute command: $($_.Exception.Message)"
        return 1
    }
}

# Show progress indicator for long-running operations
function Show-Progress {
    param(
        [string]$Activity,
        [scriptblock]$ScriptBlock
    )
    
    Write-Info "Starting: $Activity"
    
    # Start background job
    $job = Start-Job -ScriptBlock $ScriptBlock
    
    # Show progress while job runs
    $counter = 0
    $spinner = @('|', '/', '-', '\')
    
    while ($job.State -eq "Running") {
        $spinnerChar = $spinner[$counter % 4]
        Write-Host "`r$Activity... $spinnerChar" -NoNewline -ForegroundColor Yellow
        Start-Sleep -Milliseconds 250
        $counter++
    }
    
    # Clear progress line
    Write-Host "`r$(' ' * ($Activity.Length + 10))" -NoNewline
    Write-Host "`r" -NoNewline
    
    # Get job results
    $result = Receive-Job -Job $job
    Remove-Job -Job $job
    
    return $result
}

# Main setup function
function Start-Environment {
    param(
        [string]$EnvType,
        [string]$ActionType,
        [bool]$ShouldBuild,
        [bool]$ShouldDetach
    )
    
    $composeFile = Get-ComposeFile $EnvType
    
    if (-not (Test-Path $composeFile)) {
        Write-Error "Compose file not found: $composeFile"
        return $false
    }
    
    Write-Info "Using compose file: $composeFile"
    
    # Build compose command
    $composeCmd = "docker-compose -f `"$composeFile`""
    
    switch ($ActionType) {
        "up" {
            Write-Info "Starting $EnvType environment..."
            
            if ($ShouldBuild) {
                Write-Info "Building containers first..."
                $buildCmd = "$composeCmd build"
                $buildExitCode = Invoke-CommandWithOutput $buildCmd
                
                if ($buildExitCode -ne 0) {
                    Write-Error "Build failed, aborting startup"
                    return $false
                }
                
                Write-Success "Build completed successfully"
                Write-Info "Starting services..."
            }
            
            $composeCmd += " up"
            
            if ($ShouldDetach) {
                $composeCmd += " -d"
            }
        }
        "down" {
            Write-Info "Stopping $EnvType environment..."
            $composeCmd += " down"
        }
        "restart" {
            Write-Info "Restarting $EnvType environment..."
            Write-Info "Stopping services first..."
            $downExitCode = Invoke-CommandWithOutput "$composeCmd down"
            
            if ($downExitCode -eq 0) {
                Write-Info "Starting services..."
                $composeCmd += " up -d"
            } else {
                Write-Warning "Stop command had issues, attempting to start anyway..."
                $composeCmd += " up -d"
            }
        }
        "logs" {
            Write-Info "Showing logs for $EnvType environment..."
            Write-Info "Press Ctrl+C to stop following logs"
            Write-Host ""
            
            # For logs, we want to run the command directly to see real-time output
            $logsCmd = "docker-compose -f `"$composeFile`" logs -f --tail=100"
            
            try {
                # Change to the correct directory
                $originalLocation = Get-Location
                Set-Location (Split-Path $composeFile -Parent | Split-Path -Parent)
                
                Write-Command "Executing: $logsCmd"
                Write-Host "========== DOCKER COMPOSE LOGS ==========" -ForegroundColor Cyan
                
                # Run directly in console for real-time logs
                Invoke-Expression $logsCmd
                $exitCode = $LASTEXITCODE
                
                Set-Location $originalLocation
                
                Write-Host "==========================================" -ForegroundColor Cyan
                if ($exitCode -eq 0) {
                    Write-Success "Logs command completed"
                } else {
                    Write-Warning "Logs command exited with code: $exitCode"
                }
                
                return $exitCode -eq 0
            }
            catch {
                Write-Error "Failed to show logs: $($_.Exception.Message)"
                Set-Location $originalLocation
                return $false
            }
        }
        "clean" {
            Write-Warning "This will remove all containers, volumes, and networks for $EnvType environment"
            $confirmation = Read-Host "Are you sure? (y/N)"
            
            if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
                Write-Info "Cleaning up $EnvType environment..."
                $composeCmd += " down -v --remove-orphans"
            } else {
                Write-Info "Clean operation cancelled"
                return $true
            }
        }
        "build" {
            Write-Info "Building containers for $EnvType environment..."
            $composeCmd += " build --no-cache"
        }
        "status" {
            Write-Info "Checking status of $EnvType environment..."
            $composeCmd += " ps"
        }
    }
    
    # Execute the command with real-time output (except for logs which are handled separately)
    if ($ActionType -eq "logs") {
        # Logs are already handled in the switch statement above
        $exitCode = if ($? -eq $true) { 0 } else { 1 }
    } else {
        $exitCode = Invoke-CommandWithOutput $composeCmd
    }
    
    if ($exitCode -eq 0) {
        Write-Success "Command completed successfully"
        
        # Show useful information after startup
        if ($ActionType -eq "up") {
            Start-Sleep -Seconds 2  # Give services time to start
            Show-ServiceInfo $EnvType
            
            if ($ShouldDetach) {
                Write-Info "Services started in detached mode"
                Write-Info "Use '.\setup.ps1 $EnvType logs' to view logs"
                Write-Info "Use '.\setup.ps1 $EnvType status' to check service status"
            }
        }
        
        return $true
    } else {
        Write-Error "Command failed with exit code: $exitCode"
        return $false
    }
}

# Show service information
function Show-ServiceInfo {
    param([string]$EnvType)
    
    Write-Header "Service Information - $($EnvType.ToUpper())"
    
    switch ($EnvType) {
        "dev" {
            Write-Info "Service URL: http://localhost:4004"
            Write-Info "Swagger Documentation: http://localhost:4004/docs/"
            Write-Info "PostgreSQL: localhost:5432"
            Write-Info "Redis: localhost:6379"
        }
        "prod" {
            Write-Info "Service URL: http://localhost:4004"
            Write-Info "Swagger Documentation: http://localhost:4004/docs/"
            Write-Info "Nginx Proxy: http://localhost:80"
            Write-Info "PostgreSQL: localhost:5432"
            Write-Info "Redis: localhost:6379"
        }
        "stage" {
            Write-Info "Service URL: http://localhost:4005"
            Write-Info "Swagger Documentation: http://localhost:4005/docs/"
            Write-Info "PostgreSQL: localhost:5433"
            Write-Info "Redis: localhost:6380"
        }
        "test" {
            Write-Info "Service URL: http://localhost:4006"
            Write-Info "Test Reports: http://localhost:8082"
            Write-Info "PostgreSQL: localhost:5434"
            Write-Info "Redis: localhost:6381"
        }
    }
    
    Write-Info "Health Check: curl http://localhost:4004/api/scan/health"
    Write-Info "View Logs: .\setup.ps1 $EnvType logs"
    Write-Info "Stop Services: .\setup.ps1 $EnvType down"
    Write-Info "Service Status: .\setup.ps1 $EnvType status"
    
    # Test health endpoint if service is supposed to be up
    Write-Info "Testing service health..."
    
    $healthUrl = switch ($EnvType) {
        "dev" { "http://localhost:4004/health" }
        "stage" { "http://localhost:4004/health" }
        "test" { "http://localhost:4004/health" }
        default { "http://localhost:4004/health" }
    }
    
    try {
        Start-Sleep -Seconds 3  # Give service time to fully start
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10 -ErrorAction Stop
        Write-Success "Service is healthy and responding"
    }
    catch {
        Write-Warning "Service health check failed - service may still be starting up"
        Write-Info "Wait a few seconds and try: curl $healthUrl"
    }
}

# Show help information
function Show-Help {
    Write-Header "Microsoft User Extraction Service Setup"
    Write-Host ""
    Write-Host "USAGE:"
    Write-Host "  .\setup.ps1 [environment] [action] [options]"
    Write-Host ""
    Write-Host "ENVIRONMENTS:"
    Write-Host "  dev     - Development environment (default)"
    Write-Host "  prod    - Production environment"
    Write-Host "  stage   - Staging environment"
    Write-Host "  test    - Testing environment"
    Write-Host ""
    Write-Host "ACTIONS:"
    Write-Host "  up      - Start services (default)"
    Write-Host "  down    - Stop services"
    Write-Host "  restart - Restart services"
    Write-Host "  logs    - Show service logs"
    Write-Host "  clean   - Stop and remove containers/volumes"
    Write-Host "  build   - Build containers"
    Write-Host "  status  - Show container status"
    Write-Host ""
    Write-Host "OPTIONS:"
    Write-Host "  -Build  - Force rebuild containers"
    Write-Host "  -Detach - Run in detached mode"
    Write-Host ""
    Write-Host "EXAMPLES:"
    Write-Host "  .\setup.ps1                    # Start dev environment"
    Write-Host "  .\setup.ps1 dev up -Build     # Start dev with build"
    Write-Host "  .\setup.ps1 prod up -Detach   # Start prod in background"
    Write-Host "  .\setup.ps1 test up           # Run tests"
    Write-Host "  .\setup.ps1 dev logs          # View dev logs"
    Write-Host "  .\setup.ps1 prod down         # Stop production"
    Write-Host "  .\setup.ps1 dev clean         # Clean dev environment"
    Write-Host "  .\setup.ps1 dev status        # Check service status"
    Write-Host "  .\setup.ps1 dev restart       # Restart services"
}

# Main execution
function Main {
    # Show help if requested
    if ($args -contains "-h" -or $args -contains "--help" -or $args -contains "help") {
        Show-Help
        return
    }
    
    Write-Header "Microsoft User Extraction Service Setup"
    Write-Info "Environment: $Environment"
    Write-Info "Action: $Action"
    Write-Info "Build: $Build"
    Write-Info "Detach: $Detach"
    Write-Info "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    # Check prerequisites
    Write-Info "Checking prerequisites..."
    
    if (-not (Test-DockerRunning)) {
        Write-Error "Docker is not running. Please start Docker Desktop first."
        return
    }
    
    if (-not (Test-DockerCompose)) {
        Write-Error "docker-compose is not available. Please install Docker Compose."
        return
    }
    
    Write-Success "Docker and docker-compose are available"
    
    # Show Docker version info
    try {
        $dockerVersion = docker version --format "{{.Server.Version}}" 2>$null
        $composeVersion = docker-compose version --short 2>$null
        Write-Info "Docker version: $dockerVersion"
        Write-Info "Docker Compose version: $composeVersion"
    }
    catch {
        Write-Warning "Could not retrieve Docker version information"
    }
    
    # Execute the action
    $success = Start-Environment -EnvType $Environment -ActionType $Action -ShouldBuild $Build -ShouldDetach $Detach
    
    if (-not $success) {
        Write-Error "Setup failed. Check the logs above for details."
        Write-Info "For troubleshooting:"
        Write-Info "  1. Check Docker Desktop is running"
        Write-Info "  2. Verify docker-compose file exists"
        Write-Info "  3. Check port availability"
        Write-Info "  4. Review error messages above"
        exit 1
    } else {
        Write-Success "Setup completed successfully!"
        Write-Info "Completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    }
}

# Run main function
Main