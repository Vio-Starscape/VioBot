FROM python:3.11-slim

# Set the working directory
WORKDIR /app

RUN apt-get update && apt-get install -y tesseract-ocr

COPY ./requirements.txt /app
RUN pip3 install -r requirements.txt

COPY . /app

# Run the application
CMD ["python3", "main.py"]