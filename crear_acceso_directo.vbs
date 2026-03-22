Set ws = CreateObject("WScript.Shell")
escritorio = ws.SpecialFolders("Desktop")

Set s = ws.CreateShortcut(escritorio & "\Taller PULGA Fi.lnk")
s.TargetPath = "wscript.exe"
s.Arguments = """C:\taller_api\iniciar_oculto.vbs"""
s.WorkingDirectory = "C:\taller_api"
s.Description = "Iniciar Sistema Taller PULGA Fi"
s.IconLocation = "C:\Windows\System32\shell32.dll, 14"
s.Save()

MsgBox "Listo! Acceso directo creado en el escritorio." & Chr(13) & Chr(13) & "Doble clic en 'Taller PULGA Fi' para iniciar el sistema.", 64, "Taller PULGA Fi"
