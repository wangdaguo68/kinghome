FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
COPY app ./app

EXPOSE 19099
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "19099"]
