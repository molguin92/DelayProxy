FROM python:3.7.4-alpine
MAINTAINER "Manuel Olguín Muñoz <molguin@kth.se>"

COPY . /Relay/
WORKDIR /Relay
RUN pip install -r requirements.txt


