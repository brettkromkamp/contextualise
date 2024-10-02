# Pull official base image
FROM python:3.12.7-slim-bookworm

# Install Git
RUN apt-get -y update
RUN apt-get -y install git

# Set working directory
WORKDIR /usr/src/contextualise

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN pip install --upgrade pip setuptools wheel
COPY ./requirements.txt /usr/src/contextualise/requirements.txt
RUN pip install -r requirements.txt

# Copy project
COPY . /usr/src/contextualise/