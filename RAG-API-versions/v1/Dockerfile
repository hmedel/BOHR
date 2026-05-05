FROM continuumio/miniconda3:latest

WORKDIR /app

# Copiar archivos
COPY requirements.txt .
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY .env .

# Crear ambiente conda
RUN conda create -n rag-api python=3.11 -y && \
    echo "source activate rag-api" > ~/.bashrc

# Instalar dependencias
SHELL ["conda", "run", "-n", "rag-api", "/bin/bash", "-c"]
RUN conda install -c conda-forge fastapi uvicorn requests -y && \
    pip install langchain langchain-community langchain-ollama chromadb pypdf python-multipart pydantic pydantic-settings aiofiles python-dotenv

# Crear directorios
RUN mkdir -p data/chroma data/uploads logs

EXPOSE 8000

CMD ["conda", "run", "--no-capture-output", "-n", "rag-api", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
