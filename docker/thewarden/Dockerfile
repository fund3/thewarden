FROM python:3.6.7

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY . /app
WORKDIR /app

CMD ["python3", "-u", "warden.py"]
