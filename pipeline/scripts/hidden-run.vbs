' Runs the given command file with NO console window (arg 0 = path to .cmd).
' Used by the Lovanya* scheduled tasks so services can't be killed by
' accidentally closing a console window.
CreateObject("WScript.Shell").Run """" & WScript.Arguments(0) & """", 0, False
