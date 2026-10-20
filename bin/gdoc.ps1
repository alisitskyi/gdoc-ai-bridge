$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& python "$ScriptDir\..\src\gdoc_ai\cli.py" $args
