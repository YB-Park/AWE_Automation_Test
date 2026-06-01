param(
    [string] $Config = ".\configs\sample.local.json"
)

$ErrorActionPreference = "Stop"

python -m awe_gui_builder inspect --config $Config
exit $LASTEXITCODE
