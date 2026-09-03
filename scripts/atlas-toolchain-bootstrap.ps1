# Prepare a PowerShell session for Atlas Cargo builds.
#
# Dot-source this file so the environment changes remain in the current shell:
#   . .\scripts\atlas-toolchain-bootstrap.ps1
#
# Or run one command with the prepared environment:
#   .\scripts\atlas-toolchain-bootstrap.ps1 cargo nextest run
#
# RUSTC/RUSTDOC remain unset. Rustup's rustc proxy selects the committed
# rust-toolchain.toml for the current provider; a process-wide absolute path
# would silently bypass a provider pin. Empty overrides make Cargo execute
# ` -vV` and are removed here.

$env:RUSTC = $null
$env:RUSTDOC = $null

# `.cargo/config.toml` sets `target-dir`, but cargo finds that file only by
# walking up from the current directory. Running cargo from outside the stack
# with `--manifest-path` - which is how a build avoids the overlay rewriting a
# member's lockfile - finds no config and falls back to the member's own
# `target/`, forking the cache one repository at a time. Binding it to the
# session instead of to where the session stands is the part a config file
# cannot express.
if (-not $env:CARGO_TARGET_DIR) {
    $atlasRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $env:CARGO_TARGET_DIR = Join-Path $atlasRoot 'target'
}

$ucrtCandidates = @()
if ($env:MSYS2_ROOT) {
    $ucrtCandidates += (Join-Path $env:MSYS2_ROOT 'ucrt64\bin')
}
$pathEntries = if ($env:Path) { $env:Path -split [IO.Path]::PathSeparator } else { @() }
foreach ($entry in $pathEntries) {
    if ([string]::Equals((Split-Path -Leaf (Split-Path -Parent $entry)), 'ucrt64', [StringComparison]::OrdinalIgnoreCase) -and
        [string]::Equals((Split-Path -Leaf $entry), 'bin', [StringComparison]::OrdinalIgnoreCase)) {
        $ucrtCandidates += $entry
    }
}
$ucrtCandidates += @('C:\msys64\ucrt64\bin', 'D:\msys64\ucrt64\bin')
$ucrtBin = $ucrtCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -First 1
if ($ucrtBin) {
    $remaining = @($pathEntries | Where-Object { $_ -and -not [string]::Equals($_, $ucrtBin, [StringComparison]::OrdinalIgnoreCase) })
    $env:Path = (@($ucrtBin) + $remaining) -join [IO.Path]::PathSeparator
}

if ($MyInvocation.InvocationName -ne '.') {
    if ($args.Count -gt 0) {
        if ($args.Count -gt 1) {
            & $args[0] @($args[1..($args.Count - 1)])
        } else {
            & $args[0]
        }
        exit $LASTEXITCODE
    }
    $rustc = if ($env:RUSTC) { $env:RUSTC } else { '<unset>' }
    $rustdoc = if ($env:RUSTDOC) { $env:RUSTDOC } else { '<unset>' }
    Write-Output "RUSTC=$rustc"
    Write-Output "CARGO_TARGET_DIR=$env:CARGO_TARGET_DIR"
    Write-Output "RUSTDOC=$rustdoc"
    Write-Output "PATH=$env:Path"
}
