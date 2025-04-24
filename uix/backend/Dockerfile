# File: uix/backend/Dockerfile

# --- Stage 1: Install dependencies and build extensions ---
    FROM python:3.11-slim AS builder
    WORKDIR /app
    

    # Install gcc, make, Python headers for any C extensions
    RUN apt-get update \
     && apt-get install -y --no-install-recommends \
          build-essential \
          python3-dev \
     && rm -rf /var/lib/apt/lists/*
    
    # Install SSH & SCP tools
    RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*
    # Copy only requirements and install into a slim layer
    COPY requirements.txt ./
    RUN pip install --no-cache-dir -r requirements.txt
    
    # --- Stage 2: Build the final, runtime-only image ---
    FROM python:3.11-slim
    WORKDIR /app
    
    # ✅ Install SSH in the final stage!
    RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

    # 1) Copy the installed libraries
    COPY --from=builder /usr/local/lib/python3.11/site-packages \
                        /usr/local/lib/python3.11/site-packages
    
    # 2) Copy the console‐scripts (flask, etc.)
    COPY --from=builder /usr/local/bin /usr/local/bin
    
    # 3) Copy your entire project so app.py can import from root folders
    COPY . /app
    
    # Switch into the backend folder
    WORKDIR /app/uix/backend
    
    # Expose and configure Flask
    ENV FLASK_APP=app.py \
        FLASK_ENV=development \
        BACKEND_PORT=5000
    EXPOSE 5000
    
    # Start the server
    #CMD ["flask", "run", "--host=0.0.0.0", "--port=${BACKEND_PORT}"]
    CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port", "5000"]
    #CMD ["python", "-m", "flask", "run", "--port", "5000"]
