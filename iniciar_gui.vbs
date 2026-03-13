Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

sDir    = fso.GetParentFolderName(WScript.ScriptFullName)
pyFile  = sDir & "\parking_gui.py"

If Not fso.FileExists(pyFile) Then
    MsgBox "No se encuentra parking_gui.py en:" & vbCrLf & sDir, 16, "LEBL Parking"
    WScript.Quit
End If

' Buscar pythonw en rutas habituales 
Dim candidates(10)
candidates(0) = "pythonw"
candidates(1) = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python313\pythonw.exe"
candidates(2) = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
candidates(3) = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
candidates(4) = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python310\pythonw.exe"
candidates(5) = "C:\Python313\pythonw.exe"
candidates(6) = "C:\Python312\pythonw.exe"
candidates(7) = "C:\Python311\pythonw.exe"
candidates(8) = shell.ExpandEnvironmentStrings("%PROGRAMFILES%") & "\Python313\pythonw.exe"
candidates(9) = shell.ExpandEnvironmentStrings("%PROGRAMFILES%") & "\Python312\pythonw.exe"
candidates(10)= shell.ExpandEnvironmentStrings("%PROGRAMFILES%") & "\Python311\pythonw.exe"

pyExe = ""

' Primero intentar pythonw del PATH usando where.exe
On Error Resume Next
ret = shell.Run("cmd /c where pythonw >""" & sDir & "\pythonw_path.tmp"" 2>nul", 0, True)
If Err.Number = 0 And ret = 0 Then
    If fso.FileExists(sDir & "\pythonw_path.tmp") Then
        Set f = fso.OpenTextFile(sDir & "\pythonw_path.tmp", 1)
        line1 = Trim(f.ReadLine)
        f.Close
        fso.DeleteFile sDir & "\pythonw_path.tmp"
        If line1 <> "" Then pyExe = """" & line1 & """"
    End If
End If
On Error GoTo 0

' Si no está en PATH, buscar en rutas conocidas
If pyExe = "" Then
    Dim i
    For i = 1 To 10
        If fso.FileExists(candidates(i)) Then
            pyExe = """" & candidates(i) & """"
            Exit For
        End If
    Next
End If

' Si no encontramos pythonw, intentar con python normal (tendrá CMD)
If pyExe = "" Then
    On Error Resume Next
    ret = shell.Run("cmd /c where python >""" & sDir & "\python_path.tmp"" 2>nul", 0, True)
    If Err.Number = 0 And ret = 0 Then
        If fso.FileExists(sDir & "\python_path.tmp") Then
            Set f = fso.OpenTextFile(sDir & "\python_path.tmp", 1)
            line1 = Trim(f.ReadLine)
            f.Close
            fso.DeleteFile sDir & "\python_path.tmp"
            If line1 <> "" Then pyExe = """" & line1 & """"
        End If
    End If
    On Error GoTo 0
End If

If pyExe = "" Then
    MsgBox "No se encontró Python en este sistema." & vbCrLf & _
           "Instala Python desde python.org o la Microsoft Store.", _
           16, "LEBL Parking — Error"
    WScript.Quit
End If

' Lanzar la app
cmd = pyExe & " """ & pyFile & """"
shell.Run cmd, 0, False
