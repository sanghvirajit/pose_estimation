#################################################################
####################### BUILD STAGE #############################
#################################################################
# This image contains:
# 1. Multiple Python versions (3.6 and newer)
# 2. Required Python headers
# 3. C compiler and other helpful libraries commonly used for building wheels
FROM ghcr.io/alpha-affinity/snakepacker/buildtime:master as builder

# Create virtualenv
# Target folder should be the same on the build stage and on the target stage
# A VIRTUAL_ENV variable is set in the shared base image to make this easier
RUN python3.11 -m venv ${VIRTUAL_ENV} && \
    pip install -U pip setuptools wheel

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Record the required system libraries/packages
RUN find-libdeps ${VIRTUAL_ENV} > ${VIRTUAL_ENV}/pkgdeps.txt && \
	# opencv-contrib-python dependency
	echo "libgl1" >> ${VIRTUAL_ENV}/pkgdeps.txt

#################################################################
####################### TARGET STAGE ############################
#################################################################
# Use the same python version used on the build stage
FROM ghcr.io/alpha-affinity/snakepacker/runtime:3.11-master

# Copy over the venv (ensure same path as venvs are not designed to be portable)
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Install the required library packages
RUN xargs -ra ${VIRTUAL_ENV}/pkgdeps.txt apt-install

# Copy the project (everything not recorded in .dockerignore)
WORKDIR /app
COPY . .

# Command to run the app with required port
CMD ["uvicorn", "app.app:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]
