FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY app_protected.py .

EXPOSE 5000

# APP_MODULE can be overridden: app:app or app_protected:app
ARG APP_MODULE=app:app
ENV APP_MODULE=${APP_MODULE}

CMD gunicorn --workers 4 --threads 2 --bind 0.0.0.0:5000 ${APP_MODULE}
