FROM python
ENV PYTHONUNBUFFERED=1
RUN echo "import time\nfor index in range(10):\n\ttime.sleep(1)\n\tprint(index)\n" >> start.py
CMD ["python", "-u", "start.py"]