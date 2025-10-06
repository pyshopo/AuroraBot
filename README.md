# PupusasBot

# Asistente de IA "Aura" 

**Aura** es un asistente de voz personal y modular escrito en Python, impulsado por la IA generativa de Google Gemini. Está diseñado para ser fácil de entender, modificar y expandir.

##  Características Principales
* **Control por Voz:** Se activa con la palabra clave "Hola, Aura".
* **IA Conversacional:** Capaz de mantener conversaciones, contar chistes, dar consejos y responder preguntas generales.
* **Control del Sistema:** Abre aplicaciones, ajusta el volumen y gestiona la papelera de reciclaje.
* **Búsquedas Web:** Realiza búsquedas en Google, YouTube y consulta el clima.
* **Arquitectura Modular:** El código está separado en módulos lógicos (`cerebro`, `web`, `sistema`) para facilitar su mantenimiento.

---
##  Requisitos Previos

Antes de empezar, debes tener lo siguiente:

* **Python:** Versión 3.10 o superior.
* **Dependencias de Sistema (para Debian/Ubuntu):**
    ```bash
    sudo apt update && sudo apt install mpg123 alsa-utils kfind trash-cli portaudio19-dev -y
    ```

---
## Instalación y Configuración

Sigue estos pasos para poner a Aura en funcionamiento.

### 1. Clona el Repositorio
```bash
git clone [https://github.com/tu-usuario/Asistente_Aura.git](https://github.com/tu-usuario/Asistente_Aura.git)
cd Asistente_Aura
```

### 2. Crea y Activa el Entorno Virtual
```bash
python3 -m venv entorno
source entorno/bin/activate
```

### 3. Instala las Librerías de Python
Instala todas las dependencias necesarias con el archivo
`requirement.txt`.
```bash
pip install -r requirements.txt
```

### 4. Configura tu Clave API
El "cerebro" de Aura necesita una clave API de Google Gemini.

1.  Obtén tu clave gratuita desde **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2.  Abre el archivo `cerebro_ia.py`.
3.  Pega tu clave en la variable `API_KEY`:

    ```python
    API_KEY = 'TU_API_KEY'
    ```

---
##  Cómo Ejecutar a Aura

Con el entorno virtual activado, simplemente ejecuta el archivo principal:

```bash
python3 main.py
```

Aura se iniciará y estará lista para recibir la orden "Hola, Aura".

---
## 🐳¡ (Opcional) Ejecución con Docker
Si tienes problemas con tu entorno local de Python, puedes usar Docker para una ejecución garantizada y aislada.

1.  **Construye la imagen de Docker:**
    ```bash
    docker build -t aura-asistente .
    ```
2.  **Ejecuta el contenedor:**
    ```bash
    docker run -it --rm --device /dev/snd aura-asistente
    ```
*Asegúrate de tener el `Dockerfile` y `requirements.txt` en el directorio del proyecto y tu clave API configurada antes de construir la imagen.*
