# tobii_targets_lab_sdk_bridge

Aplicación en **Python 3.9.10** para el laboratorio de semana 9, con dos modos de entrada:

- `mouse` para el laboratorio virtual
- `tobii` usando el bridge **Tobii SDK cliente/servidor** (`gaze.exe` + `gaze_server.exe`)

Esta versión mantiene:

- bolitas / targets estáticos en pantalla
- selección por `dwell-time`
- configuración desde `config.json`
- exportación de logs `.log`
- soporte para mouse y rastreador Tobii

---

## 1. Estructura del proyecto

```text
.
├── config.json
├── main.py
├── README.md
├── requirements.txt
├── logs/
├── experiment/
│   ├── app.py
│   ├── config.py
│   ├── geometry.py
│   ├── logger.py
│   ├── models.py
│   └── providers.py
└── sdk_bridge/
    └── windows/
        ├── build/
        │   ├── gaze.exe
        │   ├── gaze_server.exe
        │   └── tobii_stream_engine.dll
        ├── src/
        │   ├── gaze.cpp
        │   └── gaze_server.cpp
        ├── include/
        ├── lib/
        └── run_all.bat
```

---

## 2. Qué hace cada parte importante

### Python

- `main.py`
  - punto de entrada del experimento
- `config.json`
  - configuración principal de pantalla, input, dwell-time y colores
- `experiment/app.py`
  - lógica del experimento y del flujo de trials
- `experiment/providers.py`
  - proveedor de entrada: mouse o Tobii por UDP
- `experiment/logger.py`
  - escritura del log `.log`

### Tobii SDK bridge

- `sdk_bridge/windows/src/gaze.cpp`
  - lee datos normalizados del SDK de Tobii
- `sdk_bridge/windows/src/gaze_server.cpp`
  - ejecuta `gaze.exe`, convierte los datos a pixeles y los envía por UDP a Python

---

## 3. Requisitos

### Requisitos de software

1. **Python 3.9.10**
2. **MinGW / g++** para recompilar `gaze.cpp` y `gaze_server.cpp`
3. **Windows** para usar el modo Tobii con los `.exe` incluidos
4. **Pygame** (instalado desde `requirements.txt`)

### Requisitos de hardware

- Tobii Eye Tracker conectado
- SDK y bridge funcionales en Windows

---

## 4. Instalar y verificar Python 3.9.10

### Ver qué versiones de Python tienes instaladas

En **CMD** o **PowerShell**:

```bat
py -0p
```

### Crear un entorno virtual con Python 3.9.10

Dentro de la carpeta del proyecto:

```bat
py -3.9 -m venv .venv
```

### Activar el entorno virtual

#### En CMD

```bat
.venv\Scripts\activate.bat
```

#### En PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

> Si PowerShell bloquea scripts por políticas del sistema, usa **CMD** o ejecuta Python directamente con:
>
> ```bat
> .venv\Scripts\python.exe main.py --config config.json
> ```

### Confirmar versión activa

```bat
python --version
```

Debe mostrar algo como:

```txt
Python 3.9.10
```

### Instalar dependencias

```bat
pip install -r requirements.txt
```

---

## 5. Instalar MinGW y habilitar `g++`

### Si `g++` no es reconocido

Si aparece el error:

```txt
"g++" no se reconoce como un comando interno o externo
```

entonces Windows no está encontrando MinGW en el `PATH`.

### Solución rápida para la sesión actual de CMD

Si MinGW está instalado en:

```txt
C:\mingw\bin
```

usa:

```bat
set PATH=C:\mingw\bin;%PATH%
g++ --version
```

Si responde con la versión del compilador, ya quedó habilitado para esa ventana de CMD.

### Dejarlo permanente en Windows

1. abrir **Editar las variables de entorno del sistema**
2. entrar a **Variables de entorno**
3. editar la variable `Path`
4. agregar:

```txt
C:\mingw\bin
```

5. cerrar y volver a abrir la terminal
6. verificar con:

```bat
g++ --version
```

### Si MinGW está en otra carpeta

Algunas instalaciones usan rutas como:

```txt
C:\msys64\mingw64\bin
```

En ese caso agrega esa ruta real al `PATH`.

---

## 6. Preconfiguración de los dos archivos principales del bridge

### A. `sdk_bridge/windows/src/gaze.cpp`

Este archivo lee del SDK de Tobii y entrega coordenadas **normalizadas** entre `0` y `1`.

La salida esperada tiene este formato:

```txt
Timestamp:123456789, Gaze point:0.421533, 0.615248
```

- `x` y `y` entre `0` y `1` = datos normalizados válidos
- `0.0, 0.0` = dato inválido en este flujo de trabajo

#### Para probarlo manualmente

```bat
cd sdk_bridge\windows
build\gaze.exe
```

Si no imprime nada útil, el problema está antes de Python:

- Tobii no detectado
- SDK
- compilación del bridge
- o falta de calibración / datos válidos

---

### B. `sdk_bridge/windows/src/gaze_server.cpp`

Este archivo:

1. ejecuta `gaze.exe`
2. lee sus valores normalizados
3. los convierte a pixeles usando:

```cpp
#define SCREEN_W 1920
#define SCREEN_H 1080
```

4. envía por UDP mensajes como:

```txt
TIMESTAMP_US,X_PX,Y_PX
```

#### Importante

Si cambias la resolución en este archivo, luego debes actualizar también en `config.json`:

```json
"source_screen_width_px": 1920,
"source_screen_height_px": 1080
```

#### Para probarlo manualmente

```bat
cd sdk_bridge\windows
build\gaze_server.exe
```

La salida esperada es algo como:

```txt
Socket UDP creado para enviar a 127.0.0.1:5005
Ejecutando build\gaze.exe...
Enviado: 123456789,812,533
```

---

## 7. Cómo recompilar los archivos del bridge

### Recompilar `gaze.cpp`

```bat
cd sdk_bridge\windows
g++ src\gaze.cpp -o build\gaze.exe -Iinclude -Llib\x86 -ltobii_stream_engine
```

### Recompilar `gaze_server.cpp`

```bat
cd sdk_bridge\windows
g++ src\gaze_server.cpp -o build\gaze_server.exe -Iinclude -Llib\x86 -ltobii_stream_engine -lws2_32
```

---

## 8. Configuración principal en `config.json`

### Modo de entrada

Para mouse:

```json
"input_mode": "mouse"
```

Para Tobii:

```json
"input_mode": "tobii"
```

### Sección Tobii

```json
"tobii": {
  "launch_bridge": true,
  "bridge_executable": "sdk_bridge/windows/build/gaze_server.exe",
  "bridge_cwd": "sdk_bridge/windows",
  "udp_ip": "127.0.0.1",
  "udp_port": 5005,
  "source_screen_width_px": 1920,
  "source_screen_height_px": 1080,
  "treat_zero_zero_as_invalid": true,
  "sample_stale_after_ms": 250,
  "startup_wait_ms": 1200
}
```

### Qué significa cada campo

- `launch_bridge`: Python lanza automáticamente `gaze_server.exe`
- `bridge_executable`: ruta al bridge
- `bridge_cwd`: carpeta desde donde se ejecuta el bridge
- `udp_ip`, `udp_port`: socket donde Python escucha los datos
- `source_screen_width_px`, `source_screen_height_px`: resolución usada por `gaze_server.cpp`
- `treat_zero_zero_as_invalid`: interpreta `0,0` como dato inválido
- `sample_stale_after_ms`: si no llegan paquetes recientes, la muestra se invalida

---

## 9. Otras configuraciones útiles que puedes cambiar

### A. Orden manual de los dwell-times

Para que no salga random:

```json
"condition_order": "fixed"
```

Y el orden se toma tal como aparece en `conditions`.

Si quieres empezar por el más lento:

```json
"conditions": [
  {"id": "dwell_900", "label": "900 ms", "dwell_time_ms": 900},
  {"id": "dwell_500", "label": "500 ms", "dwell_time_ms": 500},
  {"id": "dwell_250", "label": "250 ms", "dwell_time_ms": 250}
]
```

### B. Color del resalte del target activo

```json
"highlight_color": [255, 215, 0]
```

Ese valor da un amarillo visible.

### C. Todas las bolitas de un solo color

Puedes dejar solo un color y el sistema lo repetirá:

```json
"colors": [
  [80, 160, 255]
]
```

O repetir explícitamente el mismo color varias veces.

### D. Resolución de la pantalla del experimento

```json
"screen_width_px": 1440,
"screen_height_px": 900
```

### E. Tamaño y espaciado usando ángulo visual

```json
"target_radius_deg": 1.5,
"spacing_x_deg": 7.0,
"spacing_y_deg": 5.5
```

---

## 10. Cómo ejecutar el proyecto

### Opción 1 — ejecutar directamente el main

Desde la raíz del proyecto:

```bat
python main.py --config config.json
```

### Opción 2 — usando el entorno sin activarlo

```bat
.venv\Scripts\python.exe main.py --config config.json
```

### Opción 3 — usando el batch incluido

```bat
run_python_app.bat
```

---

## 11. Flujo recomendado para probar Tobii

### Paso 1
Probar primero `gaze.exe`:

```bat
cd sdk_bridge\windows
build\gaze.exe
```

Si imprime `timestamp`, `x`, `y` entre `0` y `1`, entonces Tobii + SDK están funcionando.

### Paso 2
Probar luego `gaze_server.exe`:

```bat
cd sdk_bridge\windows
build\gaze_server.exe
```

Si imprime líneas `Enviado: ...`, entonces el bridge UDP está funcionando.

### Paso 3
Ejecutar Python en modo Tobii:

```bat
python main.py --config config.json
```

---

## 12. Ejemplo de `requirements.txt`

```txt
pygame>=2.5,<3
# Optional, only if your Tobii SDK exposes the Python binding:
# tobii-research
```

---

## 13. Nota de plataforma

- en **Windows** puedes usar `mouse` y `tobii`
- en **macOS** esta versión funciona bien para `mouse`
- para usar Tobii en macOS tendrías que tener un bridge equivalente que envíe UDP y no dependa de `.exe`

---

## 14. Resumen rápido

1. instalar / verificar **Python 3.9.10**
2. crear `.venv`
3. instalar dependencias
4. instalar o configurar **MinGW / g++**
5. verificar `gaze.exe`
6. verificar `gaze_server.exe`
7. poner `"input_mode": "tobii"`
8. ejecutar:

```bat
python main.py --config config.json
```
