FROM python:3.10.6-slim-buster

WORKDIR /app

COPY . .

RUN pip install pipenv && \
    pipenv install --deploy --system && \
    pip uninstall pipenv -y

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
