FROM python:3.9-alpine
WORKDIR /app
RUN pip install requests python-dotenv pyquery argparse
COPY . .
EXPOSE 8245:80
CMD [ "python", "ddns.py" ]