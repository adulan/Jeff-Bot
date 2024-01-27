FROM python:3

WORKDIR /usr/src/app
RUN chmod -R 775 /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "./jeffbot.py" ]
