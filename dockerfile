FROM python:3.11-slim

# Set the working directory
WORKDIR /app

COPY ./requirements.txt /app
RUN pip3 install -r requirements.txt

COPY . /app

# Run the application
CMD ["python3", "main.py"]