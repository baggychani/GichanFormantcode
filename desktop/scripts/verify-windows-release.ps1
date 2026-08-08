[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,

    [Parameter(Mandatory = $true)]
    [string]$BundledSidecarPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-RequiredFile {
    param([string]$Path, [string]$Label)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $resolved -or -not (Test-Path -LiteralPath $resolved.Path -PathType Leaf)) {
        throw "$Label not found: $Path"
    }
    return $resolved.Path
}

function Get-ObjectValue {
    param($Object, [string]$Name)

    if ($null -eq $Object) {
        return $null
    }
    if ($Object -is [System.Collections.IDictionary]) {
        return $Object[$Name]
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($property) {
        return $property.Value
    }
    return $null
}

function ConvertFrom-CodePoints {
    param([int[]]$CodePoints)

    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

function Read-SidecarMessage {
    param(
        [System.Diagnostics.Process]$Process,
        [System.IO.StreamReader]$Reader,
        [scriptblock]$Predicate,
        [int]$TimeoutSeconds,
        [string]$Description
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($Process.HasExited) {
            throw "Sidecar exited before $Description (exit $($Process.ExitCode))"
        }
        $remaining = [Math]::Max(1, [int]($deadline - [DateTime]::UtcNow).TotalMilliseconds)
        $readTask = $Reader.ReadLineAsync()
        if (-not $readTask.Wait($remaining)) {
            throw "Timed out waiting for sidecar $Description"
        }
        $line = $readTask.Result
        if ($null -eq $line) {
            throw "Sidecar stdout closed before $Description"
        }
        try {
            $message = $line | ConvertFrom-Json
        }
        catch {
            Write-Host "Ignoring non-JSON sidecar output: $line"
            continue
        }
        if (& $Predicate $message) {
            return $message
        }
    }
    throw "Timed out waiting for sidecar $Description"
}

function Test-SidecarHealth {
    param([string]$SidecarPath, [string]$Label)

    $sidecar = Resolve-RequiredFile -Path $SidecarPath -Label "$Label sidecar"
    $internal = Join-Path (Split-Path -Parent $sidecar) "_internal"
    if (-not (Test-Path -LiteralPath $internal -PathType Container)) {
        throw "$Label sidecar _internal directory not found: $internal"
    }

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $sidecar
    $startInfo.Arguments = "--desktop"
    $startInfo.WorkingDirectory = Split-Path -Parent $sidecar
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Environment["PATH"] = "$env:SystemRoot\System32;$env:SystemRoot"
    $startInfo.Environment["PYTHONUTF8"] = "1"
    $startInfo.Environment["PYTHONIOENCODING"] = "utf-8"
    $startInfo.Environment["QT_QPA_PLATFORM"] = "offscreen"
    [void]$startInfo.Environment.Remove("PYTHONHOME")
    [void]$startInfo.Environment.Remove("PYTHONPATH")
    [void]$startInfo.Environment.Remove("VIRTUAL_ENV")
    [void]$startInfo.Environment.Remove("UV")

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $stderrTask = $null
    $stdinWriter = $null
    $stdoutReader = $null
    $stderrReader = $null
    $started = $false
    $verificationWord = ConvertFrom-CodePoints @(0xAC80, 0xC99D)
    $probeRoot = Join-Path ([IO.Path]::GetTempPath()) "GichanFormant release $verificationWord-$([Guid]::NewGuid().ToString('N'))"
    try {
        if (-not $process.Start()) {
            throw "Failed to start $Label sidecar"
        }
        $started = $true
        # Use explicit UTF-8 readers/writer instead of the PowerShell host or
        # .NET Framework console encoding. Windows PowerShell 5.1 lacks the
        # ProcessStartInfo.StandardInputEncoding property used by .NET Core.
        $stdinWriter = [IO.StreamWriter]::new($process.StandardInput.BaseStream, $utf8)
        $stdinWriter.AutoFlush = $true
        $stdoutReader = [IO.StreamReader]::new($process.StandardOutput.BaseStream, $utf8, $true)
        $stderrReader = [IO.StreamReader]::new($process.StandardError.BaseStream, $utf8, $true)
        $stderrTask = $stderrReader.ReadToEndAsync()

        [void](Read-SidecarMessage -Process $process -Reader $stdoutReader -TimeoutSeconds 60 -Description "ready event" -Predicate {
            param($message)
            (Get-ObjectValue -Object $message -Name "event") -eq "sidecar_ready"
        })

        $healthId = "release-health-$([Guid]::NewGuid().ToString('N'))"
        $healthRequest = @{
            v = 1
            id = $healthId
            method = "health"
            params = @{}
        } | ConvertTo-Json -Compress
        $stdinWriter.WriteLine($healthRequest)

        $health = Read-SidecarMessage -Process $process -Reader $stdoutReader -TimeoutSeconds 30 -Description "health response" -Predicate {
            param($message)
            (Get-ObjectValue -Object $message -Name "id") -eq $healthId
        }
        $healthResult = Get-ObjectValue -Object $health -Name "result"
        if (-not (Get-ObjectValue -Object $healthResult -Name "ok") -or
            (Get-ObjectValue -Object $healthResult -Name "protocol_version") -ne 1) {
            throw "$Label sidecar returned an invalid health response: $($health | ConvertTo-Json -Compress)"
        }

        # Exercise the UTF-8 process boundary and the scientific runtime from
        # a path that includes both spaces and Korean characters.
        New-Item -ItemType Directory -Path $probeRoot | Out-Null
        $probeName = ConvertFrom-CodePoints @(0xBAA8, 0xC74C, 0x20, 0xC790, 0xB8CC, 0x20, 0xAC80, 0xC99D)
        $probePath = Join-Path $probeRoot "$probeName.tsv"
        $labelI = ConvertFrom-CodePoints @(0xC774)
        $labelEo = ConvertFrom-CodePoints @(0xC5B4)
        $labelA = ConvertFrom-CodePoints @(0xC544)
        [IO.File]::WriteAllText(
            $probePath,
            "300`t2000`t/$labelI/`n400`t1800`t/$labelEo/`n500`t1500`t/$labelA/`n",
            $utf8
        )
        $loadId = "release-load-$([Guid]::NewGuid().ToString('N'))"
        $loadRequest = @{
            v = 1
            id = $loadId
            method = "load_files"
            params = @{ paths = @($probePath) }
        } | ConvertTo-Json -Compress -Depth 5
        $stdinWriter.WriteLine($loadRequest)
        $load = Read-SidecarMessage -Process $process -Reader $stdoutReader -TimeoutSeconds 120 -Description "UTF-8 load response" -Predicate {
            param($message)
            (Get-ObjectValue -Object $message -Name "id") -eq $loadId
        }
        $loadError = Get-ObjectValue -Object $load -Name "error"
        $loadResult = Get-ObjectValue -Object (Get-ObjectValue -Object $load -Name "result") -Name "load_result"
        if ($loadError -or (Get-ObjectValue -Object $loadResult -Name "success_count") -ne 1) {
            throw "$Label sidecar failed the UTF-8 path probe: $($load | ConvertTo-Json -Compress -Depth 8)"
        }

        $shutdownId = "release-shutdown-$([Guid]::NewGuid().ToString('N'))"
        $shutdownRequest = @{
            v = 1
            id = $shutdownId
            method = "shutdown"
            params = @{}
        } | ConvertTo-Json -Compress
        $stdinWriter.WriteLine($shutdownRequest)
        [void](Read-SidecarMessage -Process $process -Reader $stdoutReader -TimeoutSeconds 15 -Description "shutdown response" -Predicate {
            param($message)
            (Get-ObjectValue -Object $message -Name "id") -eq $shutdownId
        })
        if (-not $process.WaitForExit(15000)) {
            throw "$Label sidecar did not exit after shutdown"
        }
        if ($process.ExitCode -ne 0) {
            throw "$Label sidecar exited with code $($process.ExitCode)"
        }
        Write-Host "$Label sidecar health passed without Python or uv on PATH"
    }
    catch {
        $stderr = if ($stderrTask -and $stderrTask.IsCompleted) { $stderrTask.Result } else { "" }
        if ($stderr) {
            Write-Host "--- $Label sidecar stderr ---"
            Write-Host $stderr
        }
        throw
    }
    finally {
        if ($started -and -not $process.HasExited) {
            $process.Kill()
            [void]$process.WaitForExit(5000)
        }
        if ($stdinWriter) { $stdinWriter.Dispose() }
        if ($stdoutReader) { $stdoutReader.Dispose() }
        if ($stderrReader) { $stderrReader.Dispose() }
        $process.Dispose()
        if (Test-Path -LiteralPath $probeRoot) {
            Remove-Item -LiteralPath $probeRoot -Recurse -Force
        }
    }
}

function Stop-InstalledProcesses {
    param([string]$InstallRoot)

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallRoot, [StringComparison]::OrdinalIgnoreCase) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

$installer = Resolve-RequiredFile -Path $InstallerPath -Label "NSIS installer"
$bundledSidecar = Resolve-RequiredFile -Path $BundledSidecarPath -Label "Bundled sidecar"
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$installRoot = Join-Path $tempRoot "GichanFormant-installer-smoke-$([Guid]::NewGuid().ToString('N'))"
$installed = $false

try {
    # 5A: exercise the exact PyInstaller binary that Tauri will bundle while
    # Python, uv and the development virtualenv are unavailable on PATH.
    Test-SidecarHealth -SidecarPath $bundledSidecar -Label "Bundled"

    New-Item -ItemType Directory -Path $installRoot | Out-Null
    $install = Start-Process -FilePath $installer -ArgumentList @("/S", "/D=$installRoot") -PassThru -Wait
    if ($install.ExitCode -ne 0) {
        throw "NSIS silent install failed with code $($install.ExitCode)"
    }
    $installed = $true

    $installedSidecar = Get-ChildItem -LiteralPath $installRoot -Recurse -File -Filter "gichan-formant-sidecar.exe" |
        Select-Object -First 1
    if (-not $installedSidecar) {
        throw "Installed sidecar not found under $installRoot"
    }
    Test-SidecarHealth -SidecarPath $installedSidecar.FullName -Label "Installed"

    $app = Get-ChildItem -LiteralPath $installRoot -File -Filter "*.exe" |
        Where-Object {
            $_.Name -notlike "*uninstall*" -and
            $_.Name -ne "gichan-formant-sidecar.exe"
        } |
        Sort-Object @{ Expression = { if ($_.Name -match '^GichanFormant\.exe$') { 0 } else { 1 } } }, FullName |
        Select-Object -First 1
    if (-not $app) {
        throw "Installed desktop executable not found under $installRoot"
    }

    $appProcess = Start-Process -FilePath $app.FullName -WorkingDirectory $app.DirectoryName -PassThru
    Start-Sleep -Seconds 15
    if ($appProcess.HasExited) {
        throw "Installed desktop app exited during startup with code $($appProcess.ExitCode)"
    }
    Write-Host "Installed desktop startup smoke passed: $($app.FullName)"
}
finally {
    Stop-InstalledProcesses -InstallRoot $installRoot
    $uninstaller = if (Test-Path -LiteralPath $installRoot) {
        Get-ChildItem -LiteralPath $installRoot -Recurse -File -Filter "*uninstall*.exe" | Select-Object -First 1
    }
    else {
        $null
    }
    if ($installed -and $uninstaller) {
        $uninstall = Start-Process -FilePath $uninstaller.FullName -ArgumentList "/S" -PassThru -Wait
        if ($uninstall.ExitCode -ne 0) {
            Write-Warning "NSIS silent uninstall returned code $($uninstall.ExitCode)"
        }
    }

    $resolvedInstallRoot = [IO.Path]::GetFullPath($installRoot)
    $safePrefix = Join-Path $tempRoot "GichanFormant-installer-smoke-"
    if ($resolvedInstallRoot.StartsWith($safePrefix, [StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedInstallRoot)) {
        Remove-Item -LiteralPath $resolvedInstallRoot -Recurse -Force
    }
}
