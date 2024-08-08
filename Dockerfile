FROM python:3.12
LABEL authors="lion"


RUN apt update && apt install sqlite3

RUN mkdir -p /data/litman

ADD litman /app/litman
ADD litman_cli /app/litman_cli
ADD litman_web /app/litman_web
ADD scripts /app/scripts
ADD litman_docker.toml /app/litman.toml
ADD requirements.txt /app

RUN pip install -r /app/requirements.txt

WORKDIR "/app"

ENTRYPOINT ["flask", "--app", "litman_web", "run", "--host=0.0.0.0"]
