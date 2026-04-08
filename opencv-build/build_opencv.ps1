$msvcExists = Get-Command cl.exe -ErrorAction SilentlyContinue

if ($msvcExists) { 
    Write-Host 'MSVC already in path.' -ForegroundColor Green
} else { 
    Write-Host 'MSVC missing. Searching for Visual Studio...' -ForegroundColor Cyan
    
    $currentArch = $env:PROCESSOR_ARCHITECTURE.ToLower()
    # Use Join-Path instead of string interpolation to avoid quote errors
    $vswherePath = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    
    if (Test-Path $vswherePath) {
        $vsPath = & $vswherePath -latest -products * -property installationPath
        
        if ($vsPath) {
            $devShellDll = Join-Path $vsPath 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll'
            
            if (Test-Path $devShellDll) {
                Import-Module $devShellDll
                Write-Host "Entering Developer Shell (Arch: $currentArch)..." -ForegroundColor Green
                Enter-VsDevShell -VsInstallPath $vsPath -SkipAutomaticLocation -arch $currentArch
            }
        }
    }
}

$finalCl = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $finalCl) {
    Write-Host 'CRITICAL: cl.exe not found. Please run in a Developer PowerShell or install Build Tools.' -ForegroundColor Red
    Write-Host 'Installing MSVC...' -ForegroundColor Cyan
    winget install --id Microsoft.VisualStudio.BuildTools --source winget --exact --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
    return
}

$is64 = [Environment]::Is64BitProcess
Write-Host "Is 64bit Process? $is64" -ForegroundColor Cyan

$RegOutput = reg query "HKLM\SOFTWARE\GStreamer1.0" /s /reg:64 /v InstallDir 2>$null
$GstSource = $null
foreach ($line in $RegOutput) {
    # We look for the 'REG_SZ' marker. 
    # \s{2,} looks for 2 or more spaces/tabs (the gutter between the type and the path).
    # (.*) then captures EVERYTHING after that gutter, including spaces in 'Program Files'.
    if ($line -match 'REG_SZ\s{2,}(.*)$') {
        $GstSource = $matches[1].Trim()
        break
    }
}

if (-not $GstSource -or -not (Test-Path "$GstSource")) {
    winget install gstreamerproject.gstreamer --override "/SetupType=full /Silent Tasks=install_vcredist,environment_variables,registry_install_dir"
    return
}

$PythonVer = if ($args[0]) { $args[0] } else { "3.11" }
$env:UV_PYTHON = $PythonVer

$ProjectRoot = Get-Location
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
if (Test-Path "uv.lock") { Remove-Item -Force "uv.lock" }

$OpencvWrapper = "$ProjectRoot\vendored\opencv-python"
$BuildDir = "$ProjectRoot\build\opencv_python_cp$($PythonVer -replace '\.', '')"
$WheelOutDir = "$ProjectRoot\wheelhouse"
$WheelFinalDir = "$ProjectRoot\wheels"

if (-not (Test-Path "$OpencvWrapper\opencv\CMakeLists.txt")) {
    Write-Host "Updating submodules..." -ForegroundColor Cyan
    git submodule update --init --recursive --depth 1
}

Write-Host "Setting up build environment for Python $PythonVer..." -ForegroundColor Cyan
uv sync
# Activate uv virtualenv for this session
$env:VIRTUAL_ENV = "$ProjectRoot\.venv"
$env:PATH = "$ProjectRoot\.venv\Scripts;$env:PATH"

$PythonExe = (Get-Command python).Source

$GstCMakePath = $GstSource -replace '\\', '/'

$BackendPath = "$OpencvWrapper\_build_backend"
$env:PYTHONPATH = "$OpencvWrapper;$BackendPath;$env:PYTHONPATH"

$env:CMAKE_ARGS = "-D WITH_GSTREAMER=ON " + `
                  "-D ENABLE_PRECOMPILED_HEADERS=OFF " + `
                  "-D GSTREAMER_DIR=""$GstCMakePath"" " + `
                  "-D PYTHON3_EXECUTABLE=""$($PythonExe -replace '\\', '/')"" " + `
                  "-D BUILD_opencv_python3=ON " + `
                  "-D BUILD_opencv_gapi=ON " + `
                  "-D INSTALL_PYTHON_EXAMPLES=OFF " + `
                  "-D BUILD_EXAMPLES=OFF " + `
                  "-D BUILD_TESTS=OFF " + `
                  "-D BUILD_PERF_TESTS=OFF " + `
                  "-D OPENCV_ENABLE_NONFREE=ON " + `
                  "-D CMAKE_BUILD_TYPE=Release"

Set-Location $OpencvWrapper

Write-Host "Performing deep clean..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "_skbuild") { Remove-Item -Recurse -Force "_skbuild" }
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
$env:SKBUILD_BUILD_DIR = $BuildDir

Write-Host "Launching build for Python $PythonVer..." -ForegroundColor Green
python -m pip wheel . --verbose -w dist

if (-not (Test-Path $WheelOutDir)) { New-Item -ItemType Directory $WheelOutDir }
$GeneratedWheel = Get-ChildItem "dist\opencv*.whl" | Select-Object -First 1

if ($GeneratedWheel) {
    Copy-Item $GeneratedWheel.FullName "$WheelOutDir\$($GeneratedWheel.Name)"
    Write-Host "------------------------------------------------" -ForegroundColor Green
    Write-Host "Build Successful: $($GeneratedWheel.Name)"
    Write-Host "------------------------------------------------" -ForegroundColor Green
}

Set-Location $ProjectRoot
python patch_opencv.py "$WheelOutDir\$($GeneratedWheel.Name)" -o "$WheelFinalDir"
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
if (Test-Path "uv.lock") { Remove-Item -Force "uv.lock" }