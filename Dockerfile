FROM python:3.11-slim

WORKDIR /service

# Install CPU-only torch first — must happen before sentence-transformers
# otherwise pip resolves the default CUDA torch (~2.5 GB instead of ~200 MB)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    torch==2.3.0+cpu \
    torchvision==0.18.0+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Now install the rest — sentence-transformers will reuse the cpu torch above
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app/ ./app/

# Create mount points for Docker volumes
RUN mkdir -p /app/chromadb /app/models

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]