FROM python:3.9 
WORKDIR /usr/src/app
COPY . .
RUN pip install requests python-dotenv pyquery argparse
EXPOSE 8245:8245
CMD [ "python", "ddns.py" ]