# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install the required packages
RUN pip install -r requirements.txt

# Copy the rest of the working directory contents into the container
COPY . .

# Specify the entrypoint
CMD ["python", "imgops.py"]