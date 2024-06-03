# Usa una base image con Python
FROM python:3.9-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file di progetto nel container
COPY . .

# Copia il file delle credenziali nel container
COPY key/project-uma-59328-f7ae5187b4a7.json /app/service-account-file.json

# Imposta la variabile d'ambiente per le credenziali
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service-account-file.json"

# Aggiorna pip
RUN pip install --upgrade pip

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Esponi la porta su cui il server web sarà in ascolto
EXPOSE 8080

# Comando per avviare l'applicazione
CMD ["python", "main.py"]
