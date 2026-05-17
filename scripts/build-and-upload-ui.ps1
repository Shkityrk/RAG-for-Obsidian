# Сборка UI на Windows и загрузка dist на сервер (обход OOM на VPS 2 GB).
# Usage:
#   .\scripts\build-and-upload-ui.ps1 -ServerIp "203.0.113.10" -DeployUser "deploy" -AppUrl "http://203.0.113.10"

param(
    [Parameter(Mandatory = $true)]
    [string] $ServerIp,

    [string] $DeployUser = "deploy",
    [string] $DeployPath = "/opt/RAG-for-Obsidian",
    [Parameter(Mandatory = $true)]
    [string] $AppUrl,

    [string] $SshKeyPath = "$env:USERPROFILE\.ssh\gha_deploy"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$UiDir = Join-Path $RepoRoot "client\ui"

Push-Location $UiDir
$env:VITE_APPLICATION_MODE = "prod"
$env:VITE_API_BASE_URL = $AppUrl
npm ci
npm run build
Pop-Location

$DistDir = Join-Path $UiDir "dist"
ssh -i $SshKeyPath "${DeployUser}@${ServerIp}" "mkdir -p ${DeployPath}/client/ui/dist && rm -rf ${DeployPath}/client/ui/dist/*"
scp -i $SshKeyPath -r "${DistDir}\*" "${DeployUser}@${ServerIp}:${DeployPath}/client/ui/dist/"

Write-Host "UI dist uploaded to ${DeployPath}/client/ui/dist"
Write-Host "Run on server: SKIP_UI_BUILD=true bash ${DeployPath}/scripts/deploy-remote.sh"
