# Start with a Python image that has pipenv installed
FROM python:3.11 as builder

# Install pipenv
RUN pip3 install pipenv

# Set working directory
WORKDIR /app

# Copy all files from the current directory to the container
COPY . ./

# Generate requirements.txt
RUN pipenv requirements > requirements.txt

# Now, start the next stage of the Dockerfile to build your actual application image
FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR /app

# Update the system and install necessary packages
RUN yum update -y && \
    yum install -y python3 curl libcom_err ncurses expat libblkid libuuid libmount ffmpeg libsm6 libxext6 git && \
    yum clean all

# Upgrade pip and install wheel
RUN pip3 install --upgrade pip && \
    pip3 install wheel

# Copy the generated requirements.txt from the builder stage
COPY --from=builder /app/requirements.txt /app/

# Copy all files from the builder stage to the current working directory in the final image
COPY --from=builder /app /app

# Install dependencies 
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy the entire application directory to the Lambda task root
COPY ./ ${LAMBDA_TASK_ROOT}/

# Set the command to run your application
CMD [ "app.main.handler" ]
