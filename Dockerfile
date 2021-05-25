FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN pip install .

ENTRYPOINT ["python", "-m", "ska_sdp_proccontrol"]
