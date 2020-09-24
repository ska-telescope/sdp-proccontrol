FROM python:3.7

WORKDIR /app
COPY . ./

RUN pip install -r requirements.txt
RUN pip install .

ENTRYPOINT ["python", "-m", "ska_sdp_proccontrol"]
