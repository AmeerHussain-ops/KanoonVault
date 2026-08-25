# KanoonVault Windows Testing Helper Script
# Usage: .\test-windows-builds.ps1 -Phase build|test|verify|release

param(
    [ValidateSet('build', 'test', 'verify', 'release')]
    [string]$Phase = 'verify',
    
    [string]$Version = '1.0.0',
    [string]$ReleaseNotes = 'Release notes here',
    [switch]$SkipPreChecks
)

function Write-Step { param([string]$Message); Write-Host "▶ $Message" -ForegroundColor Cyan }
function Write-Success { param([string]$Message); Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Error_ { param([string]$Message); Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Warning_ { param([string]$Message); Write-Host "⚠️  $Message" -ForegroundColor Yellow }

# ============================================================================
# PRE-CHECK: Environment validation
# ============================================================================
function Test-Environment {
    Write-Step "Validating environment..."
    
    $checks = @{
        'Python 3.10+' = { python --version 2>&1 | Select-String '3\.10' }
        'Git' = { git --version 2>&1 }
        'Inno Setup 6' = { Test-Path 'C:\Program Files (x86)\Inno Setup 6' }
        'Workspace' = { Test-Path '.\launcher.py' }
    }
    
    foreach ($check in $checks.GetEnumerator()) {
        try {
            $result = & $check.Value
            if ($result) {
                Write-Success $check.Name
            } else {
                Write-Error_ "$($check.Name) not found"
                return $false
            }
        } catch {
            Write-Error_ "$($check.Name) check failed: $_"
            return $false
        }
    }
    
    return $true
}

# ============================================================================
# PHASE 1: BUILD
# ============================================================================
function Build-Installer {
    Write-Step "Starting build process..."
    
    if (-not $SkipPreChecks) {
        if (-not (Test-Environment)) {
            Write-Error_ "Environment checks failed. Fix issues and retry."
            exit 1
        }
    }
    
    # Run build script
    Write-Step "Executing build_windows_package.bat..."
    & ".\build_windows_package.bat"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error_ "Build failed with exit code $LASTEXITCODE"
        exit 1
    }
    
    # Verify output
    if (Test-Path "installer-output\KanoonVault-Setup.exe") {
        $fileSize = (Get-Item "installer-output\KanoonVault-Setup.exe").Length / 1MB
        Write-Success "Installer created: $($fileSize)MB"
        return $true
    } else {
        Write-Error_ "Installer not found after build"
        return $false
    }
}

# ============================================================================
# PHASE 2: TEST
# ============================================================================
function Test-Installer {
    Write-Step "Testing installer..."
    
    $installerPath = "installer-output\KanoonVault-Setup.exe"
    
    if (-not (Test-Path $installerPath)) {
        Write-Error_ "Installer not found. Run 'build' phase first."
        return $false
    }
    
    # Verify file integrity
    Write-Step "Verifying installer integrity..."
    $fileSize = (Get-Item $installerPath).Length
    Write-Success "Installer size: $([math]::Round($fileSize / 1MB))MB"
    
    # Calculate checksum
    Write-Step "Generating checksum..."
    $hash = certutil -hashfile $installerPath SHA256 | Select-Object -Index 1
    Write-Success "SHA256: $hash"
    
    # Save checksum
    $hash | Out-File -FilePath "installer-output\CHECKSUM.txt" -Force
    Write-Success "Checksum saved to CHECKSUM.txt"
    
    # Test run (if requested interactively)
    Write-Host ""
    Write-Warning_ "Manual testing required:"
    Write-Host "1. Double-click: $installerPath"
    Write-Host "2. Run through Inno Setup wizard"
    Write-Host "3. Follow first-launch wizard (Welcome → Storage → API Key)"
    Write-Host "4. Verify application starts and works"
    Write-Host ""
    
    return $true
}

# ============================================================================
# PHASE 3: VERIFY
# ============================================================================
function Verify-Installation {
    Write-Step "Verifying installed application..."
    
    $installPath = "C:\Program Files\KanoonVault"
    $appDataPath = "$env:APPDATA\Roaming\.kanoonvault"
    $storagePath = "$env:LOCALAPPDATA\KanoonVault"
    
    # Check installation directory
    if (Test-Path $installPath) {
        Write-Success "Installation directory found: $installPath"
        
        $launcher = Join-Path $installPath "launcher.exe"
        if (Test-Path $launcher) {
            Write-Success "Launcher executable found"
        } else {
            Write-Warning_ "launcher.exe not found in installation"
        }
    } else {
        Write-Warning_ "Installation directory not found. Run installer first."
        return $false
    }
    
    # Check AppData configuration
    if (Test-Path $appDataPath) {
        Write-Success "AppData directory found: $appDataPath"
        
        $configFile = Join-Path $appDataPath "storage-config.json"
        if (Test-Path $configFile) {
            Write-Success "Storage configuration found"
            
            try {
                $config = Get-Content $configFile -Raw | ConvertFrom-Json
                Write-Success "  Storage Dir: $($config.storage_dir)"
                Write-Success "  First Run Complete: $($config.first_run_complete)"
            } catch {
                Write-Error_ "Failed to parse config: $_"
            }
        } else {
            Write-Warning_ "storage-config.json not found (expected after first launch)"
        }
    } else {
        Write-Warning_ "AppData directory not found (expected after first launch)"
    }
    
    # Check user storage directory
    if (Test-Path $storagePath) {
        Write-Success "User storage directory found: $storagePath"
        
        $subdirs = Get-ChildItem -Path $storagePath -Directory | Select-Object -ExpandProperty Name
        Write-Success "  Subdirectories: $($subdirs -join ', ')"
    } else {
        Write-Warning_ "User storage directory not found (expected after first launch)"
    }
    
    return $true
}

# ============================================================================
# PHASE 4: RELEASE
# ============================================================================
function Create-Release {
    param(
        [string]$Version = '1.0.0',
        [string]$Notes = 'KanoonVault Windows Release'
    )
    
    Write-Step "Preparing GitHub release..."
    
    $installerPath = "installer-output\KanoonVault-Setup.exe"
    
    if (-not (Test-Path $installerPath)) {
        Write-Error_ "Installer not found. Run 'build' phase first."
        return $false
    }
    
    if (-not (Test-Path "installer-output\CHECKSUM.txt")) {
        Write-Warning_ "CHECKSUM.txt not found. Generating..."
        Test-Installer | Out-Null
    }
    
    # Display instructions
    Write-Host ""
    Write-Step "Release preparation checklist:"
    Write-Host "1. ✅ Installer ready: $installerPath"
    Write-Host "2. ✅ Checksum ready: installer-output\CHECKSUM.txt"
    Write-Host "3. ⏳ Next: Create GitHub release"
    Write-Host ""
    
    Write-Host "Quick steps:"
    Write-Host "  1. Go to: https://github.com/AmeerHussain-ops/KanoonVault/releases/new"
    Write-Host "  2. Tag: v$Version"
    Write-Host "  3. Title: KanoonVault Windows v$Version"
    Write-Host "  4. Description: [Copy from BUILD_AND_TEST_GUIDE.md]"
    Write-Host "  5. Attach file: $installerPath"
    Write-Host "  6. Publish!"
    Write-Host ""
    
    Write-Success "Release preparation complete"
    return $true
}

# ============================================================================
# MAIN: Execute requested phase
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       KanoonVault Windows Testing Helper               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

switch ($Phase) {
    'build' {
        Write-Host "PHASE: Build Windows Installer" -ForegroundColor Yellow
        Write-Host ""
        Build-Installer
    }
    'test' {
        Write-Host "PHASE: Test Installer" -ForegroundColor Yellow
        Write-Host ""
        Test-Installer
    }
    'verify' {
        Write-Host "PHASE: Verify Installation" -ForegroundColor Yellow
        Write-Host ""
        Verify-Installation
    }
    'release' {
        Write-Host "PHASE: Prepare GitHub Release" -ForegroundColor Yellow
        Write-Host ""
        Create-Release -Version $Version
    }
    default {
        Write-Error_ "Unknown phase: $Phase"
        exit 1
    }
}

Write-Host ""
