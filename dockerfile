
# Start with a Python image that has pipenv installed
FROM python:3.11 as builder

# Install pipenv
RUN pip3 install pipenv

# Copy your Pipfile and Pipfile.lock
WORKDIR /app
COPY Pipfile Pipfile.lock ./

# Generate requirements.txt
RUN pipenv requirements > requirements.txt

# Now, start the next stage of the Dockerfile to build your actual application image
FROM public.ecr.aws/lambda/python:3.11

WORKDIR /app

RUN yum update -y
RUN yum update -y python3 curl libcom_err ncurses expat libblkid libuuid libmount
RUN yum install ffmpeg libsm6 libxext6 python3-pip git -y

# Copy the generated requirements.txt from the previous stage
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Continue with your application setup...
COPY ./ ${LAMBDA_TASK_ROOT}/


CMD [ "app.main.handler" ]
