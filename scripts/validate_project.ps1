[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$terraformDirectory = Join-Path `
    $projectRoot `
    "infrastructure\terraform"

function Invoke-ValidationStep {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }

    Write-Host "PASS: $Name" -ForegroundColor Green
}

Push-Location $projectRoot

try {
    Invoke-ValidationStep `
        -Name "Validate normalized sample event" `
        -Command {
            python tests\validate_sample_events.py
        }

    Invoke-ValidationStep `
        -Name "Validate synthetic GuardDuty fixtures" `
        -Command {
            python tests\validate_guardduty_fixtures.py
        }

    Invoke-ValidationStep `
        -Name "Run finding normalizer unit tests" `
        -Command {
            python tests\test_finding_normalizer.py
        }

    Invoke-ValidationStep `
        -Name "Run AI prompt builder unit tests" `
        -Command {
            python tests\test_prompt_builder.py
        }

    Invoke-ValidationStep `
        -Name "Run AI investigator unit tests" `
        -Command {
            python tests\test_ai_investigator.py
        }

    Invoke-ValidationStep `
        -Name "Run evidence collector unit tests" `
        -Command {
            python tests\test_evidence_collector.py
        }

    Invoke-ValidationStep `
        -Name "Validate AI investigation schema" `
        -Command {
            python tests\test_ai_investigation_schema.py
        }

    Invoke-ValidationStep `
        -Name "Run AI investigation persistence tests" `
        -Command {
            python tests\test_ai_investigation_persistence.py
        }

    Invoke-ValidationStep `
        -Name "Check Terraform formatting" `
        -Command {
            terraform `
                "-chdir=$terraformDirectory" `
                fmt `
                -check
        }

    Invoke-ValidationStep `
        -Name "Validate Terraform configuration" `
        -Command {
            terraform `
                "-chdir=$terraformDirectory" `
                validate
        }

    Invoke-ValidationStep `
        -Name "Check unstaged Git changes" `
        -Command {
            git diff --check
        }

    Invoke-ValidationStep `
        -Name "Check staged Git changes" `
        -Command {
            git diff --cached --check
        }

    Write-Host ""
    Write-Host "PROJECT VALIDATION: PASS" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "PROJECT VALIDATION: FAIL" -ForegroundColor Red
    Write-Error $_
    exit 1
}
finally {
    Pop-Location
}
