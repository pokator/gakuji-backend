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

# Update the system and install necessary packages
RUN yum update -y && \
    yum install -y python3 curl libcom_err ncurses expat libblkid libuuid libmount ffmpeg libsm6 libxext6 git && \
    yum clean all

# Upgrade pip and install wheel
RUN pip3 install --upgrade pip && \
    pip3 install wheel

# Copy the generated requirements.txt from the previous stage
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Continue with your application setup...
COPY ./ ${LAMBDA_TASK_ROOT}/

CMD [ "app.main.handler" ]
