#!/usr/bin/env pwsh
# Run a cargo command across every package workspace under repos/.
# Usage: pwsh scripts/build-all.ps1 [cargo-subcommand] [extra args...]
#   pwsh scripts/build-all.ps1            # cargo build
#   pwsh scripts/build-all.ps1 test       # cargo test
#   pwsh scripts/build-all.ps1 clippy --all-targets -- -D warnings

$ErrorActionPreference = 'Stop'
$cmd = if ($args.Count -ge 1) { $args[0] } else { 'build' }
$rest = if ($args.Count -ge 2) { $args[1..($args.Count - 1)] } else { @() }

$root = Split-Path -Parent $PSScriptRoot
$repos = Join-Path $root 'repos'

$manifests = Get-ChildItem -Path $repos -Directory |
    ForEach-Object { Join-Path $_.FullName 'Cargo.toml' } |
    Where-Object { Test-Path $_ }

if (-not $manifests) { Write-Error "No package workspaces found under $repos"; exit 1 }

$failed = @()
foreach ($m in $manifests) {
    $pkg = Split-Path -Parent $m | Split-Path -Leaf
    Write-Host "==> cargo $cmd ($pkg)" -ForegroundColor Cyan
    & cargo $cmd --manifest-path $m @rest
    if ($LASTEXITCODE -ne 0) { $failed += $pkg }
}

if ($failed) { Write-Error "Failed: $($failed -join ', ')"; exit 1 }
Write-Host "All packages succeeded: cargo $cmd" -ForegroundColor Green
