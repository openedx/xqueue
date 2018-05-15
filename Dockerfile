FROM python:2.7

ENV PYTHONUNBUFFERED 1

EXPOSE 8000

WORKDIR /app

COPY ./requirements.txt .
RUN pip install -r requirements.txt

ENV DJANGO_SETTINGS_MODULE 'xqueue.docker_settings'

COPY . .

RUN mkdir -p /log && mkdir /db -p

CMD bash -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
