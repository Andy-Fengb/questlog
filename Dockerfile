FROM python:3.11-slim
WORKDIR /app
COPY app.py config.py db.py utils.py ./
COPY routes/ ./routes/
COPY services/ ./services/
COPY templates/ ./templates/
COPY static/ ./static/
RUN pip install flask gunicorn --no-cache-dir
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
