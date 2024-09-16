FROM python:3.10-slim

# Set environment variable to ensure output is flushed
ENV PYTHONUNBUFFERED=1

# Update the package list and install Tesseract OCR along with its dependencies
RUN apt-get update \
  && apt-get -y install tesseract-ocr libtesseract-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Expose port 5000 (Flask default)
EXPOSE 5000

# Define environment variable for Flask app
ENV FLASK_APP=app.py

# Run the Flask app
CMD ["python", "app.py"]
