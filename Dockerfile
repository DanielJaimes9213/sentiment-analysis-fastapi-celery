# 1. Imagen base oficial de Python
FROM python:3.12-slim

# 2. Copiar el ejecutable oficial de uv directamente
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 3. Directorio de trabajo
WORKDIR /app

# 4. Capa de dependencias: copiamos el archivo e instalamos con uv
COPY requirements.txt .
# --system instala los paquetes directo en el entorno global del contenedor
RUN uv pip install --system -r requirements.txt

# 5. Capa de código de la aplicación
COPY main.py tasks.py constants.py .

# 6. Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
