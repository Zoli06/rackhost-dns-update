FROM python:3.9 
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install requests python-dotenv pyquery argparse
COPY . .
EXPOSE 8245:80
CMD [ "python", "ddns.py" ]