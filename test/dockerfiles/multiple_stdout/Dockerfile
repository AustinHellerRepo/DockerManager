FROM python
ENV PYTHONUNBUFFERED=1
RUN echo "print('first')\nprint('second')" >> start.py
CMD ["python", "-u", "start.py"]