## SmartHome Energy Management System
Full self-sufficient system containing smart home energy simulation as REST API. <br>

### Steps to run app in developer mode

First you need to configure .env file. Example .env-example is included. <br>
<br>
In folder with docker-compose.yml run the following commands: <br>
`docker-compose build` to install all requirements <br>
`docker-compose up` to run local server ("localhost:8666/") <br>

Additional docker.sh file is included. <br>
`./docker.sh migrate` to apply migrations <br>
`./docker.sh tests` to run unit tests <br>
`./docker.sh admin` to create superuser account <br>


### Simulation - available endpoints

**User accounts management:** <br>
`/api/auth/users/` user list and create view <br>
`/api/auth/users/me/` currently logged-in user's detail <br>
`/api/auth/users/<id>/` chosen user detail <br>
`/api/auth/jwt/create/` create jwt token for user login <br>
`api/auth/jwt/refresh/` refresh jwt token <br>
`api/auth/jwt/verify/` verify jwt token <br>

**SmartHome management:** <br>
User can see only his building and it's parts (rooms, scenes, devices etc) <br>
`/api/buildings/` all user's buildings list view {GET, POST} <br>
`/api/buildings/<id>/` selected building detail view {GET, PUT, PATCH, DELETE} <br>
`/api/buildings/<id>/energy/` selected building energy data {GET} <br>
`/api/rooms/` all user's building's rooms list view {GET, POST} <br>
`/api/rooms/<id>/` selected room detail view {GET, PUT, PATCH, DELETE} <br>
`/api/devices/` all user's building's devices list view {GET, POST} <br>
`/api/devices/<id>/` selected device detail view {GET, PUT, PATCH, DELETE} <br>

**Using django-admin:**<br>
`/admin/` - endpoint for nice django interface for easy creating new buildings and stuff <br>
