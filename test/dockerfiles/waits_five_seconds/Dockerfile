FROM python
ENV PYTHONUNBUFFERED=1
RUN echo "import time\ntime.sleep(5)" >> start.py
CMD ["python", "-u", "start.py"]