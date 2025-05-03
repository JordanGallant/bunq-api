These are the for running the api of our application built with Fast API

1. Clone the Repository.
```bash
git clone https://github.com/JordanGallant/bunq-api.git
cd bunq-api
```

2. create a virtual environment in python
```bash
python -m venv env
```
3. activate the virtual environment
Mac:
```bash
source env/bin/activate 
```
Windows:
```bash
.\env\Scripts\Activate.ps1
```

4.  install dependencies using pip
```bash
pip install requirements.txt
```
5.  start the server
```bash
uvicorn main:app --reload
```

- We have deployed the API using Render.
Type in the URL: https://bunq-api.onrender.com to see the available endpoints
