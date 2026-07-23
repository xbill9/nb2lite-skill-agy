# nb2lite-agent — MCP stdio server for gemini-3.1-flash-lite-image.
# Contains only the MCP server and its open-source deps (no Claude Code, no keys).
# Run with -i (stdio transport) and pass the key via the environment:
#   docker run --rm -i -e GEMINI_API_KEY xbill9/nb2lite-agent
# Mount your project at the same absolute path so saved-image paths are valid
# on the host: -v "$PWD:$PWD" -w "$PWD"  (see README "Docker" section).
FROM python:3.12-slim

COPY requirements.txt /opt/nb2lite/requirements.txt
RUN pip install --no-cache-dir -r /opt/nb2lite/requirements.txt

COPY server.py /opt/nb2lite/server.py

# Default output dir when no workdir mount is used; harmless when -w overrides it.
WORKDIR /images
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/opt/nb2lite/server.py"]
