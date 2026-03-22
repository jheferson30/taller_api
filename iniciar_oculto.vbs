Set ws = CreateObject("WScript.Shell")

' Arrancar el servidor en background sin ventana
ws.Run "powershell -WindowStyle Hidden -Command ""Set-Location 'C:\taller_api'; .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 *> 'C:\taller_api\taller.log'""", 0, False

' Esperar 4 segundos a que arranque
WScript.Sleep 4000

' Abrir el navegador
ws.Run "http://localhost:8000", 1, False
