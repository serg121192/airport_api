FROM python:3.14.2-alpine3.23

LABEL maintainer="serg.k.ie101@gmail.com"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

RUN mkdir -p /files/media

RUN adduser \
    --disabled-password \
    --no-create-home \
    admin

RUN chown -R admin /files/media
RUN chmod -R 0755 /files/media

USER admin
