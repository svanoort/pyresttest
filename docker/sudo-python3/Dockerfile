FROM python:3.4.3-wheezy
MAINTAINER svanoort <samvanoort@gmail.com>

RUN apt-get update
RUN apt-get install -y sudo
RUN useradd mysudoer -u @@MYUSERID@@
RUN echo 'mysudoer ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers