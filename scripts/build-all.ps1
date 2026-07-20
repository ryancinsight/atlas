#!/usr/bin/env pwsh
# Run a cargo command across every package workspace recorded in .gitmodules.
# Usage: pwsh scripts/build-all.ps1 [cargo-subcommand] [extra args...]
#   pwsh scripts/build-all.ps1            # cargo build
#   pwsh scripts/build-all.ps1 nextest run # cargo nextest run
#   pwsh scripts/build-all.ps1 test --doc # cargo test --doc
#   pwsh scripts/build-all.ps1 clippy --all-targets -- -D warnings

$ErrorActionPreference = 'Stop'
$cmd = if ($args.Count -ge 1) { $args[0] } else { 'build' }
$rest = if ($args.Count -ge 2) { $args[1..($args.Count - 1)] } else { @() }

if ($cmd -eq 'test' -and -not ($rest -contains '--doc')) {
    throw "Use 'nextest run' for tests; 'test --doc' is reserved for doctests."
}

$root = Split-Path -Parent $PSScriptRoot
$moduleRows = & git -C $root config -f .gitmodules --get-regexp '^submodule\..*\.path$'
if ($LASTEXITCODE -ne 0 -or -not $moduleRows) {
    Write-Error "No package paths recorded in $root/.gitmodules"
    exit 1
}

$manifests = foreach ($row in $moduleRows) {
    $modulePath = ($row -split '\s+', 2)[1]
    $manifest = Join-Path (Join-Path $root $modulePath) 'Cargo.toml'
    if (-not (Test-Path -LiteralPath $manifest)) {
        Write-Error "Recorded package is not initialized or has no manifest: $modulePath"
        exit 1
    }
    $manifest
}

$failed = @()
foreach ($m in $manifests) {
    $pkg = Split-Path -Parent $m | Split-Path -Leaf
    Write-Host "==> cargo $cmd ($pkg)" -ForegroundColor Cyan
    & cargo $cmd --manifest-path $m @rest
    if ($LASTEXITCODE -ne 0) { $failed += $pkg }
}

if ($failed) { Write-Error "Failed: $($failed -join ', ')"; exit 1 }
Write-Host "All packages succeeded: cargo $cmd" -ForegroundColor Green
