FROM python:3.9-alpine3.12 as builder

COPY ./requirements.txt /tmp/requirements.txt
RUN apk add ffmpeg gcc libffi-dev libressl-dev musl-dev &&\
    pip3 install --no-warn-script-location --user -r /tmp/requirements.txt &&\
    adduser -S bot -s /bin/nologin -u 1000 &&\
    chown -R 1000 /root/.local

FROM python:3.9-alpine3.12 as runner

RUN apk add --no-cache ffmpeg && \
    adduser -S bot  -s /bin/nologin -u 1000
USER 1000

COPY ./bot.py /home/bot/bot.py
COPY ./backends/ /home/bot/backends/
COPY --from=builder /root/.local /home/bot/.local

WORKDIR /home/bot/
CMD python3 ./bot.py
