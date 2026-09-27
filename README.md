# SWE-Fall-26


| GitHub User  | Student Name |
| ------------- | ------------- |
| Paperbottle11  | Jayden Patel  |
| JamesRMathis  | James Mathis  |
| Sapiet1  | Chiking Vang  |
| palmersarah  | Sarah Palmer |
| NguyenA24  | Andrew Nguyen  |


Project Structure
SWE-Fall-26  
├── app.py  
├── docker-compose.yml  
├── requirements.txt  
├── init-db/  
&nbsp;│&emsp;&emsp;└── seed.sql  
└── modules/  
&emsp;&emsp;├── db.py  
&emsp;&emsp;└── udp.py.  
    
- app.py - Flask application
- modules/db.py - PostgreSQL database operations
- modules/udp.py - UDP communication
- docker-compose.yml - Local PostgreSQL development setup
- init-db/seed.sql - Initial local database setup

## Project Setup

Run the setup script

```
./start.sh
```

The application will be available at `http://127.0.0.1:8000`

## Dev Environment

We made our own database docker container so that local devs could work on the app without having to be on the VM. The command to start the container is:

```
docker compose up --build -d
```

The local database uses:

Database: photon  
User: student  
Host: 127.0.0.1  
Port: 5432  

The database is initialized using the files in init-db/.

Database data is stored in a Docker volume and will persist between restarts.
