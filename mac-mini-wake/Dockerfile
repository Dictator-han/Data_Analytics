FROM python:3.12-alpine

WORKDIR /app

COPY wake.py server.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8787

CMD ["python", "server.py"]
