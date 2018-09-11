# Use an official Python runtime as a parent image
FROM amazonlinux 

# Set the working directory to /app
WORKDIR /app

# Copy needed files into the container at /app
ADD glass_blade_dashboard_collector_local.py /app/.
ADD glass_processor_local.py /app/.
ADD lambda_simulator.py /app/.
ADD stash.py /app/.
ADD queue_utils.py /app/.
ADD requirements.txt /app/.


# Install any needed packages specified in requirements.txt
RUN yum update -y; yum install -y python3 sudo procps; pip3 install --trusted-host pypi.python.org -r requirements.txt --user; 

# Run app.py when the container launches
ENTRYPOINT /bin/bash 
