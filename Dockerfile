FROM python:3.7

WORKDIR /app
COPY . dist ./

RUN pip install -r requirements.txt -f .
RUN pip install .

ENTRYPOINT ["python", "-m", "ska_sdp_proccontrol"]
