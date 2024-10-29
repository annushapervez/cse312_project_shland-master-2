FROM python:3.8

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

#Dont have that when i deploy my final project

EXPOSE 27017

ENV FLASK_APP=my_flask.py
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.1/wait /wait
RUN chmod +x /wait

CMD /wait && python3 -u ./my_flask.py