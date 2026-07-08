FROM ubuntu:22.04

RUN apt-get update && apt-get install -y squid

COPY squid.conf /etc/squid/squid.conf

CMD ["squid", "-N", "-f", "/etc/squid/squid.conf"]
