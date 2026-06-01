param(
    [Parameter(Mandatory=$true)] [string] $InputAwj,
    [Parameter(Mandatory=$true)] [string] $OutputDir,
    [string] $Config = ".\configs\sample.local.json"
)

$ErrorActionPreference = "Stop"

python -m awe_gui_builder build --config $Config --input $InputAwj --output $OutputDir
exit $LASTEXITCODE
