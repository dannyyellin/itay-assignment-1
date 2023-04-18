FROM python:alpine3.17
# try it with FROM python:3 and see difference in image size
# make ./app a "clean" directory to store files for the container
WORKDIR ./app
RUN pip install flask
RUN pip install flask_restful
RUN pip install requests
RUN pip install simplejson
ENV FLASK_APP=meals.py
ENV FLASK_RUN_PORT=80
ADD meals.py .
ADD meal_exceptions.py .
ADD My_Ninja_key.py .
Add Ninja_key.py .
EXPOSE 80

CMD ["flask", "run", "--host=0.0.0.0"]
# try
# ENV FLASK_RUN_HOST=0.0.0.0
# CMD ["flask", "run"]
