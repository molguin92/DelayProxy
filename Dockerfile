FROM python:3.7.4-stretch
MAINTAINER "Manuel Olguín Muñoz <molguin@kth.se>"

RUN apt-get update -y && apt-get install -y build-essential g++ gcc
RUN pip install --upgrade pip

COPY . /Relay/
WORKDIR /Relay
RUN chmod +x ./main.py
RUN pip install -r requirements.txt


CMD /Relay/main.py --help
