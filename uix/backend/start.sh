export $(grep -v '^#' ../../.env | xargs) && \
python -m uvicorn main:app --reload --port $BACKEND_PORT
