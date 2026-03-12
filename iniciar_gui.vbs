Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
sDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run "pythonw """ & sDir & "\parking_gui.py""", 0, False
