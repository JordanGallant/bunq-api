# MCP Server for an Bunq Ai Agent
This Api is built with fast api and self authenticates via bunqs sandbox api, there are 4 main steps this includes signing transactions to make payments: https://doc.bunq.com/
it provides context to our AI agent that, dynamically creates an avatar based off of how much money you have in your account, 

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
