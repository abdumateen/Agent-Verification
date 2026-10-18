FROM python:3.12.7-slim
WORKDIR /opt/app
COPY src /opt/app/src
COPY tests /opt/app/tests
COPY examples /opt/app/examples
COPY policies /opt/app/policies
COPY Makefile requirements.lock .python-version /opt/app/
ENV PYTHONPATH=/opt/app/src PYTHONDONTWRITEBYTECODE=1
RUN python -m unittest discover -s tests -v
USER 65534:65534
CMD ["python", "-m", "verifygate.cli", "--help"]
