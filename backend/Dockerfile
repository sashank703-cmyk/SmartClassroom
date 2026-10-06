FROM python:3.13-slim
 
WORKDIR /app
 
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
 
COPY requirements.txt .
 
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
 
COPY . .
 
RUN mkdir -p storage/assignment_questions \
    storage/student_submissions
 
EXPOSE 8000
 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
 
