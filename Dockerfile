FROM python

WORKDIR /project

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

COPY /backend /backend

ENV PYTHONPATH=/project

CMD ["python", "backend/main.py"]
