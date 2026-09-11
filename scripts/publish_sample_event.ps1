[CmdletBinding()]
param(
    [ValidateSet("high", "medium")]
    [string]$Severity = "high",

    [string]$Profile = "ai-cybersecurity-lab-dev",

    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$terraformDirectory = Join-Path $projectRoot "infrastructure\terraform"
$fixturePath = Join-Path `
    $projectRoot `
    "sample-events\guardduty-finding-$Severity.json"

$previousAwsProfile = $env:AWS_PROFILE
$tempPath = $null

try {
    if (-not (Test-Path -LiteralPath $fixturePath)) {
        throw "Fixture not found: $fixturePath"
    }

    $env:AWS_PROFILE = $Profile

    & aws sts get-caller-identity `
        --profile $Profile `
        --region $Region `
        --output json *> $null

    if ($LASTEXITCODE -ne 0) {
        throw "AWS authentication failed. Run: aws login --profile $Profile"
    }

    $fixture = Get-Content -LiteralPath $fixturePath -Raw |
        ConvertFrom-Json

    if ($fixture.source -ne "com.danrodcor.securitylab.guardduty") {
        throw "Unexpected event source in fixture: $($fixture.source)"
    }

    if ($fixture.'detail-type' -ne "Synthetic GuardDuty Finding") {
        throw "Unexpected detail-type in fixture."
    }

    $eventBus = & terraform `
        "-chdir=$terraformDirectory" `
        output `
        -raw `
        security_event_bus_name

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($eventBus)) {
        throw "Terraform could not obtain the EventBridge bus name."
    }

    $entry = [ordered]@{
        Source       = $fixture.source
        DetailType   = $fixture.'detail-type'
        Detail       = (
            $fixture.detail |
                ConvertTo-Json -Depth 100 -Compress
        )
        EventBusName = $eventBus
    }

    $entriesJson = ConvertTo-Json `
        -InputObject @($entry) `
        -Depth 100 `
        -Compress

    $tempFilename = (
        "ai-cybersecurity-lab-put-events-{0}.json" -f
        [guid]::NewGuid()
    )

    $tempPath = Join-Path $env:TEMP $tempFilename

    [System.IO.File]::WriteAllText(
        $tempPath,
        $entriesJson,
        [System.Text.UTF8Encoding]::new($false)
    )

    $responseLines = & aws events put-events `
        --entries "file://$tempPath" `
        --region $Region `
        --profile $Profile `
        --output json

    if ($LASTEXITCODE -ne 0) {
        throw "The EventBridge PutEvents request failed."
    }

    $responseText = $responseLines -join [Environment]::NewLine
    $response = $responseText | ConvertFrom-Json

    if ($response.FailedEntryCount -ne 0) {
        throw (
            "EventBridge rejected one or more entries: {0}" -f
            $responseText
        )
    }

    $eventId = $response.Entries[0].EventId

    if ([string]::IsNullOrWhiteSpace($eventId)) {
        throw "EventBridge did not return an EventId."
    }

    [pscustomobject]@{
        Status       = "PASS"
        Severity     = $Severity
        FindingType  = $fixture.detail.type
        EventBusName = $eventBus
        EventId      = $eventId
    }
}
finally {
    if (
        $null -ne $tempPath -and
        (Test-Path -LiteralPath $tempPath)
    ) {
        Remove-Item -LiteralPath $tempPath
    }

    if ($null -eq $previousAwsProfile) {
        Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue
    }
    else {
        $env:AWS_PROFILE = $previousAwsProfile
    }
}
